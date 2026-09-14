from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sop import SopDocument, SopProcess, SopProcessChunk, SopProcessingStatus
from app.services.embeddings.factory import get_embedding_provider


def _process_result(process: SopProcess, document: SopDocument, score: float, content: str) -> dict[str, Any]:
    return {
        "process_id": str(process.id),
        "document_id": str(document.id),
        "document_title": document.title,
        "process_key": process.process_key,
        "title": process.title,
        "description": process.description,
        "trigger_phrases": process.trigger_phrases or [],
        "steps": process.steps or [],
        "tools": process.tools or [],
        "score": score,
        "content": content,
    }


def _keyword_search(db: Session, query: str, *, limit: int) -> list[dict[str, Any]]:
    """Fallback when embeddings are unavailable (e.g. freshly seeded demo SOPs)."""
    q = query.lower()
    rows = (
        db.query(SopProcess, SopDocument)
        .join(SopDocument, SopProcess.document_id == SopDocument.id)
        .filter(
            SopDocument.active.is_(True),
            SopDocument.enabled.is_(True),
            SopDocument.processing_status == SopProcessingStatus.ready,
        )
        .all()
    )
    scored: list[tuple[float, SopProcess, SopDocument]] = []
    for process, document in rows:
        haystack = " ".join(
            [
                process.title or "",
                process.description or "",
                " ".join(process.trigger_phrases or []),
                document.title or "",
            ]
        ).lower()
        score = 0.0
        for token in [t for t in q.replace("?", " ").split() if len(t) > 2]:
            if token in haystack:
                score += 0.18
        for phrase in process.trigger_phrases or []:
            if phrase.lower() in q or q in phrase.lower():
                score += 0.45
        if score > 0:
            scored.append((min(score, 0.99), process, document))
    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, process, document in scored[:limit]:
        content = f"{process.title}\n{process.description}\nTriggers: {', '.join(process.trigger_phrases or [])}"
        results.append(_process_result(process, document, score, content))
    return results


def search_sop_processes(db: Session, query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    limit = top_k or settings.sop_search_top_k
    try:
        embedder = get_embedding_provider()
        query_vec = embedder.embed_query(query)
        distance = SopProcessChunk.embedding.cosine_distance(query_vec)
        rows = (
            db.execute(
                select(SopProcessChunk, SopProcess, SopDocument, distance.label("distance"))
                .join(SopProcess, SopProcessChunk.process_id == SopProcess.id)
                .join(SopDocument, SopProcess.document_id == SopDocument.id)
                .where(
                    SopDocument.active.is_(True),
                    SopDocument.enabled.is_(True),
                    SopDocument.processing_status == SopProcessingStatus.ready,
                    SopProcessChunk.embedding.is_not(None),
                )
                .order_by(distance.asc())
                .limit(limit)
            )
            .all()
        )
    except Exception:  # noqa: BLE001
        return _keyword_search(db, query, limit=limit)

    results: list[dict[str, Any]] = []
    seen: set[UUID] = set()
    for chunk, process, document, distance_value in rows:
        if process.id in seen:
            continue
        seen.add(process.id)
        score = 1.0 - float(distance_value)
        results.append(_process_result(process, document, score, chunk.content))

    if not results:
        return _keyword_search(db, query, limit=limit)
    return results


def process_to_prompt_block(process: dict[str, Any]) -> str:
    steps = process.get("steps") or []
    step_lines = []
    for idx, step in enumerate(steps, start=1):
        tool = step.get("tool")
        line = f"{idx}. [{step.get('type', 'inform')}] {step.get('instruction', '')}"
        if tool:
            line += f" — use tool `{tool}`"
        step_lines.append(line)
    tools = ", ".join(f"`{t}`" for t in (process.get("tools") or []))
    return (
        f"### Active SOP Process: {process.get('title')}\n"
        f"Document: {process.get('document_title')}\n"
        f"Description: {process.get('description')}\n"
        f"Allowed tools ONLY: {tools or '(none)'}\n"
        f"Follow these steps in order. Ask the user when a step is ask_user or confirm. "
        f"Do not invent APIs. Do not call tools outside the allowed list.\n"
        f"Steps:\n" + "\n".join(step_lines)
    )
