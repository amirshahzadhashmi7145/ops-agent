"""Seed Meridian KB articles, SOP documents, and agent rules, then embed."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.data.support_playbook import AGENT_RULES, CATEGORIES, KB_ARTICLES, SEED_USER, SOP_DOCUMENTS
from app.models.agent_rule import AgentRule, AgentRuleCategory
from app.models.agent_settings import SETTINGS_ROW_ID, AgentSettings
from app.models.kb import KbChunk, KbProcessingStatus, KbReference
from app.models.sim import SimDevice, SimDeviceProfile, SimOrder, SimSubscription
from app.models.sop import (
    SopCategory,
    SopDocument,
    SopProcess,
    SopProcessChunk,
    SopProcessingStatus,
)
from app.services.agent_settings_defaults import DEFAULT_SYSTEM_PROMPT
from app.services.embeddings.factory import get_embedding_provider
from app.services.kb_chunker import chunk_markdown, compute_content_hash
from app.services.sop_ingestion import _build_chunk_content

logger = logging.getLogger(__name__)

PROFILES_PATH = Path(__file__).resolve().parent.parent / "data" / "device_profiles.json"

LEGACY_SEED_USERS = ("system@nexar.ops", "system@ops.internal", SEED_USER)
SERIAL_RENAMES = {
    "NX-PRO-30001": "MD-LATCH-30001",
    "NX-BEAM-10001": "MD-KEY-10001",
    "NX-ONE-20022": "MD-GUARD-20022",
    "NX-BEAM-10088": "MD-GUARD2-10088",
    "B2-MINI-50001": "MD-MINI-50001",
    "NX-FLEET-90001": "MD-FLEET-90001",
    "AC-APEX-30001": "MD-LATCH-30001",
    "AC-SCOUT-10001": "MD-KEY-10001",
    "AC-HORIZON-20022": "MD-GUARD-20022",
    "AC-SCOUT2-10088": "MD-GUARD2-10088",
    "AC-MINI-50001": "MD-MINI-50001",
    "AC-FLEET-90001": "MD-FLEET-90001",
}
DEVICE_MODEL_RENAMES = {
    "Nexar Beam": "Key",
    "Nexar One": "Guard",
    "Nexar Pro": "Latch",
    "Beam": "Key",
    "Beam2": "Guard 2",
    "Beam2 mini": "Guard Mini",
    "One": "Guard",
    "Pro": "Latch",
    "Scout": "Key",
    "Scout 2": "Guard 2",
    "Scout Mini": "Guard Mini",
    "Horizon": "Guard",
    "Apex": "Latch",
}
PLAN_RENAMES = {
    "Nexar Pro Monthly": "Guard Monthly",
    "Nexar Basic Monthly": "Basic Monthly",
    "Nexar Pro Annual": "Guard Annual",
    "Nexar Annual Plan": "Annual Plan",
    "Nexar Monthly Plan": "Monthly Plan",
    "Pro Monthly": "Guard Monthly",
    "Pro Annual": "Guard Annual",
    "Apex Monthly": "Guard Monthly",
    "Apex Annual": "Guard Annual",
}
TAG_RENAMES = {
    "nexar-beam": "key",
    "nexar-one": "guard",
    "scout": "key",
    "horizon": "guard",
}


def sync_playbook_content(db: Session | None = None) -> dict[str, int]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        categories = _sync_categories(session)
        kb_updated = _sync_kb_articles(session)
        sop_updated = _sync_sop_documents(session)
        rules = _sync_agent_rules(session)
        removed = _purge_removed_seed_content(session)
        branding = _genericize_runtime_branding(session)
        profiles = _sync_device_profiles(session)
        counts = {
            "categories": categories,
            "kb_articles_updated": kb_updated,
            "kb_articles_total": session.query(KbReference).count(),
            "sop_documents_updated": sop_updated,
            "sop_documents_total": session.query(SopDocument).count(),
            "agent_rules": rules,
            "removed_legacy": removed,
            "branding": branding,
            "profiles": profiles,
        }
        session.commit()
        logger.info("Support playbook seed complete: %s", counts)
        return counts
    except Exception:
        session.rollback()
        logger.exception("Support playbook seed failed")
        raise
    finally:
        if owns_session:
            session.close()


def _purge_removed_seed_content(db: Session) -> int:
    keep_kb = {article["title"] for article in KB_ARTICLES}
    keep_sop = {document["title"] for document in SOP_DOCUMENTS}
    removed = 0
    for row in db.query(KbReference).filter(KbReference.created_by.in_(LEGACY_SEED_USERS)).all():
        if row.title not in keep_kb:
            db.delete(row)
            removed += 1
    for row in db.query(SopDocument).filter(SopDocument.created_by.in_(LEGACY_SEED_USERS)).all():
        if row.title not in keep_sop:
            db.delete(row)
            removed += 1
    db.flush()
    return removed


def _genericize_runtime_branding(db: Session) -> int:
    updated = 0
    for old, new in SERIAL_RENAMES.items():
        updated += (
            db.query(SimDevice)
            .filter(SimDevice.serial_number == old)
            .update({SimDevice.serial_number: new}, synchronize_session=False)
        )
    for old, new in DEVICE_MODEL_RENAMES.items():
        updated += (
            db.query(SimDevice)
            .filter(SimDevice.model == old)
            .update({SimDevice.model: new}, synchronize_session=False)
        )
    for old, new in PLAN_RENAMES.items():
        updated += (
            db.query(SimSubscription)
            .filter(SimSubscription.plan_name == old)
            .update({SimSubscription.plan_name: new}, synchronize_session=False)
        )
    for order in db.query(SimOrder).all():
        changed = False
        tags = list(order.tags or [])
        new_tags = [TAG_RENAMES.get(str(tag), tag) for tag in tags]
        if new_tags != tags:
            order.tags = new_tags
            changed = True
        rma = order.rma_url or ""
        if "getnexar.com" in rma:
            order.rma_url = rma.replace("returns.getnexar.com", "returns.example.com")
            changed = True
        if changed:
            updated += 1
    settings_row = db.get(AgentSettings, SETTINGS_ROW_ID)
    if settings_row:
        name = settings_row.agent_name or ""
        if any(token in name for token in ("Nexar", "AetherCam", "Aether")):
            settings_row.agent_name = "Ops Agent"
            updated += 1
        prompt = settings_row.system_prompt or ""
        needs_prompt_refresh = any(
            token in prompt for token in ("Nexar", "AetherCam", "connected cameras")
        ) or "Ground every policy claim" not in prompt
        if needs_prompt_refresh:
            settings_row.system_prompt = DEFAULT_SYSTEM_PROMPT
            updated += 1
    db.flush()
    return updated


def _sync_device_profiles(db: Session) -> int:
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    updated = 0
    for serial, payload in profiles.items():
        device = db.query(SimDevice).filter(SimDevice.serial_number == serial).first()
        if not device:
            continue
        if payload.get("model") and device.model != payload["model"]:
            device.model = payload["model"]
        row = db.query(SimDeviceProfile).filter(SimDeviceProfile.device_id == device.id).first()
        if row is None:
            row = SimDeviceProfile(device_id=device.id)
            db.add(row)
        row.segment = payload.get("segment") or "consumer"
        row.camera_family = payload.get("camera_family") or "connect"
        row.model = payload.get("model") or device.model
        row.lookup_json = payload.get("lookup")
        row.classic_diagnostic_json = payload.get("classic_diagnostic")
        row.health_json = payload.get("health")
        row.sim_triage_json = payload.get("sim_triage")
        row.sim_data_json = payload.get("sim_data")
        updated += 1
    db.flush()
    return updated


def _sync_categories(db: Session) -> int:
    ensured = 0
    for item in CATEGORIES:
        row = db.query(SopCategory).filter(SopCategory.slug == item["slug"]).first()
        if row:
            row.name = item["name"]
            row.description = item["description"]
        else:
            db.add(
                SopCategory(
                    slug=item["slug"],
                    name=item["name"],
                    description=item["description"],
                )
            )
        ensured += 1
    db.flush()
    return ensured


def _sync_kb_articles(db: Session) -> int:
    embedder = get_embedding_provider()
    updated = 0
    for article in KB_ARTICLES:
        title = article["title"]
        markdown = article["markdown"].strip()
        content_hash = compute_content_hash(markdown)
        row = (
            db.query(KbReference)
            .options(joinedload(KbReference.chunks))
            .filter(KbReference.title == title, KbReference.created_by.in_(LEGACY_SEED_USERS))
            .first()
        )
        if row is None:
            row = KbReference(
                title=title,
                raw_text=markdown,
                created_by=SEED_USER,
                content_hash=content_hash,
            )
            db.add(row)
            db.flush()

        chunks = list(row.chunks or [])
        already_indexed = (
            row.content_hash == content_hash
            and row.processing_status == KbProcessingStatus.ready
            and row.markdown
            and chunks
            and all(chunk.embedding is not None for chunk in chunks)
        )
        if already_indexed:
            continue

        row.raw_text = markdown
        row.markdown = markdown
        row.summary = article.get("summary") or ""
        row.source_url = article.get("source_url")
        row.created_by = SEED_USER
        row.content_hash = content_hash
        row.enabled = True
        row.active = True
        row.processing_error = None
        row.updated_at = datetime.now(timezone.utc)

        db.query(KbChunk).filter(KbChunk.reference_id == row.id).delete()
        db.flush()

        parsed = chunk_markdown(markdown)
        texts = []
        for chunk in parsed:
            path = " > ".join(chunk.heading_path) if chunk.heading_path else "Document"
            texts.append(f"{path}\n\n{chunk.content}")
        vectors = embedder.embed_documents(texts) if texts else []
        for chunk, vector in zip(parsed, vectors, strict=True):
            db.add(
                KbChunk(
                    reference_id=row.id,
                    chunk_index=chunk.chunk_index,
                    heading_path=chunk.heading_path,
                    content=chunk.content,
                    embedding=vector,
                )
            )
        row.embedding_model = embedder.model_name
        row.processing_status = KbProcessingStatus.ready
        updated += 1
        db.flush()
    return updated


def _sync_sop_documents(db: Session) -> int:
    embedder = get_embedding_provider()
    updated = 0
    for document in SOP_DOCUMENTS:
        category = db.query(SopCategory).filter(SopCategory.slug == document["category_slug"]).one()
        title = document["title"]
        raw_text = document["raw_text"].strip()
        content_hash = compute_content_hash(raw_text)
        row = (
            db.query(SopDocument)
            .options(joinedload(SopDocument.processes).joinedload(SopProcess.chunks))
            .filter(SopDocument.title == title, SopDocument.created_by.in_(LEGACY_SEED_USERS))
            .first()
        )
        if row is None:
            row = SopDocument(
                title=title,
                raw_text=raw_text,
                created_by=SEED_USER,
                content_hash=content_hash,
                category_id=category.id,
            )
            db.add(row)
            db.flush()

        processes = list(row.processes or [])
        chunk_embeddings_ok = all(
            chunk.embedding is not None for process in processes for chunk in (process.chunks or [])
        ) and any(process.chunks for process in processes)
        already_indexed = (
            row.content_hash == content_hash
            and row.processing_status == SopProcessingStatus.ready
            and chunk_embeddings_ok
        )
        if already_indexed:
            row.category_id = category.id
            continue

        row.category_id = category.id
        row.raw_text = raw_text
        row.markdown = raw_text
        row.summary = document.get("summary") or ""
        row.created_by = SEED_USER
        row.content_hash = content_hash
        row.enabled = True
        row.active = True
        row.tool_warnings = []
        row.processing_error = None
        row.updated_at = datetime.now(timezone.utc)

        for process in processes:
            db.delete(process)
        db.flush()

        for index, process_data in enumerate(document["processes"]):
            process = SopProcess(
                document_id=row.id,
                process_key=process_data["process_key"],
                title=process_data["title"],
                description=process_data["description"],
                trigger_phrases=process_data["trigger_phrases"],
                steps=process_data["steps"],
                tools=process_data["tools"],
                sort_order=index,
            )
            db.add(process)
            db.flush()
            content = _build_chunk_content(process_data)
            vector = embedder.embed_documents([content])[0]
            db.add(SopProcessChunk(process_id=process.id, content=content, embedding=vector))

        row.embedding_model = embedder.model_name
        row.processing_status = SopProcessingStatus.ready
        updated += 1
        db.flush()
    return updated


def _sync_agent_rules(db: Session) -> int:
    db.query(AgentRule).filter(AgentRule.created_by.in_(LEGACY_SEED_USERS)).delete()
    for item in AGENT_RULES:
        db.add(
            AgentRule(
                category=AgentRuleCategory(item["category"]),
                content=item["content"],
                created_by=SEED_USER,
            )
        )
    db.flush()
    return len(AGENT_RULES)
