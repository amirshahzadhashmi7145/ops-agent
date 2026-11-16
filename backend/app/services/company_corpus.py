"""Load and apply multi-company demo corpora for grounding checks.

Each JSON pack under app/data/companies/ is a standalone Articles corpus.
The default runtime playbook remains Cobalt Home; these packs are used by
multi-company evaluation and can temporarily replace seed Articles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.kb import KbChunk, KbProcessingStatus, KbReference
from app.services.embeddings.factory import get_embedding_provider
from app.services.kb_chunker import chunk_markdown, compute_content_hash
from app.services.usage.semantic_cache import clear_semantic_cache

COMPANIES_DIR = Path(__file__).resolve().parent.parent / "data" / "companies"
SEED_USER = "system@ops.internal"


def list_company_ids() -> list[str]:
    return sorted(p.stem for p in COMPANIES_DIR.glob("*.json"))


def load_company(company_id: str) -> dict[str, Any]:
    path = COMPANIES_DIR / f"{company_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown company corpus: {company_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_all_companies() -> list[dict[str, Any]]:
    return [load_company(cid) for cid in list_company_ids()]


def apply_company_articles(db: Session, company: dict[str, Any]) -> dict[str, int]:
    """Replace seed Articles with this company's pack and re-embed."""
    embedder = get_embedding_provider()
    keep_titles = {a["title"] for a in company["articles"]}

    # Remove other seed articles so retrieval can't bleed brands.
    removed = 0
    for row in (
        db.query(KbReference)
        .filter(KbReference.created_by == SEED_USER)
        .all()
    ):
        if row.title not in keep_titles:
            db.delete(row)
            removed += 1
    db.flush()

    updated = 0
    for article in company["articles"]:
        title = article["title"]
        markdown = str(article["markdown"]).strip()
        content_hash = compute_content_hash(markdown)
        row = (
            db.query(KbReference)
            .options(joinedload(KbReference.chunks))
            .filter(KbReference.title == title, KbReference.created_by == SEED_USER)
            .first()
        )
        if row is None:
            row = KbReference(
                title=title,
                raw_text=markdown,
                created_by=SEED_USER,
                content_hash="",
            )
            db.add(row)
            db.flush()

        chunks = list(row.chunks or [])
        already = (
            row.content_hash == content_hash
            and row.processing_status == KbProcessingStatus.ready
            and row.markdown
            and chunks
            and all(chunk.embedding is not None for chunk in chunks)
        )
        if already:
            continue

        row.raw_text = markdown
        row.markdown = markdown
        row.summary = article.get("summary") or ""
        row.source_url = article.get("source_url")
        row.content_hash = content_hash
        row.enabled = True
        row.active = True
        row.processing_error = None
        db.query(KbChunk).filter(KbChunk.reference_id == row.id).delete()
        db.flush()
        parsed = chunk_markdown(markdown)
        texts = [
            f"{(' > '.join(c.heading_path) if c.heading_path else 'Document')}\n\n{c.content}"
            for c in parsed
        ]
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

    cleared = clear_semantic_cache(db)
    db.commit()
    return {"updated": updated, "removed": removed, "cache_cleared": cleared, "articles": len(keep_titles)}
