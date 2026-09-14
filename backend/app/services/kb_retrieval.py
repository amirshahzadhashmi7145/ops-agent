from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.kb import KbChunk, KbProcessingStatus, KbReference
from app.services.embeddings.factory import get_embedding_provider


@dataclass
class KbSearchResult:
    reference_id: UUID
    title: str
    heading_path: list[str]
    content: str
    score: float


def _searchable_filter():
    return (
        KbReference.active.is_(True),
        KbReference.enabled.is_(True),
        KbReference.processing_status == KbProcessingStatus.ready,
    )


def _keyword_candidates(db: Session, query: str, *, limit: int) -> list["KbSearchResult"]:
    """Token-overlap fallback used when embedding/vector search is unavailable, so a KB
    question still returns grounded results instead of failing the whole turn."""
    tokens = [t for t in query.lower().replace("?", " ").split() if len(t) > 2]
    rows = (
        db.execute(
            select(KbChunk, KbReference)
            .join(KbReference, KbChunk.reference_id == KbReference.id)
            .where(*_searchable_filter())
        )
        .all()
    )
    scored: list[KbSearchResult] = []
    for chunk, reference in rows:
        haystack = f"{reference.title} {chunk.content}".lower()
        score = sum(0.1 for token in tokens if token in haystack)
        if score > 0:
            scored.append(
                KbSearchResult(
                    reference_id=reference.id,
                    title=reference.title,
                    heading_path=list(chunk.heading_path or []),
                    content=chunk.content,
                    score=min(score, 0.99),
                )
            )
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def search_knowledge_base(db: Session, query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    limit = top_k or settings.kb_search_top_k
    try:
        embedder = get_embedding_provider()
        query_vector = embedder.embed_query(query)
        stmt = (
            select(
                KbChunk,
                KbReference,
                KbChunk.embedding.cosine_distance(query_vector).label("distance"),
            )
            .join(KbReference, KbChunk.reference_id == KbReference.id)
            .where(*_searchable_filter())
            .order_by("distance")
            .limit(limit * settings.kb_candidate_multiplier)
        )
        rows = db.execute(stmt).all()
        candidates = [
            KbSearchResult(
                reference_id=reference.id,
                title=reference.title,
                heading_path=list(chunk.heading_path or []),
                content=chunk.content,
                score=float(1 - distance),
            )
            for chunk, reference, distance in rows
        ]
    except Exception:  # noqa: BLE001
        candidates = _keyword_candidates(db, query, limit=limit * settings.kb_candidate_multiplier)

    results = _select_diverse_sections(
        candidates,
        limit=limit,
        max_per_reference=settings.kb_max_sections_per_reference,
    )

    expanded = _expand_sections(db, results)
    return _cap_payload(expanded)


def _select_diverse_sections(
    candidates: list[KbSearchResult],
    *,
    limit: int,
    max_per_reference: int,
) -> list[KbSearchResult]:
    """Pick up to ``limit`` distinct sections, favoring diversity across articles.

    Candidates must be pre-sorted best-first. Steps:
    1. Collapse to one (best-scoring) hit per section.
    2. First pass: take sections in score order, but skip any article that has
       already contributed ``max_per_reference`` sections (defer the rest).
    3. Backfill: if slots remain, add the deferred sections (still score-ordered),
       ignoring the cap — so a single dominant article is never starved when no
       other articles are relevant.
    """
    seen_sections: set[tuple[UUID, tuple[str, ...]]] = set()
    unique: list[KbSearchResult] = []
    for hit in candidates:
        section_key = (hit.reference_id, tuple(hit.heading_path))
        if section_key in seen_sections:
            continue
        seen_sections.add(section_key)
        unique.append(hit)

    selected: list[KbSearchResult] = []
    deferred: list[KbSearchResult] = []
    per_reference: dict[UUID, int] = {}
    for hit in unique:
        if len(selected) >= limit:
            break
        if max_per_reference > 0 and per_reference.get(hit.reference_id, 0) >= max_per_reference:
            deferred.append(hit)
            continue
        selected.append(hit)
        per_reference[hit.reference_id] = per_reference.get(hit.reference_id, 0) + 1

    for hit in deferred:
        if len(selected) >= limit:
            break
        selected.append(hit)

    return selected


def _expand_sections(db: Session, hits: list[KbSearchResult]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for hit in hits:
        siblings = (
            db.execute(
                select(KbChunk)
                .join(KbReference, KbChunk.reference_id == KbReference.id)
                .where(
                    KbChunk.reference_id == hit.reference_id,
                    KbChunk.heading_path == hit.heading_path,
                    *_searchable_filter(),
                )
                .order_by(KbChunk.chunk_index.asc())
            )
            .scalars()
            .all()
        )
        content = "\n\n".join(chunk.content for chunk in siblings)
        expanded.append(
            {
                "reference_id": str(hit.reference_id),
                "title": hit.title,
                "heading_path": hit.heading_path,
                "content": content,
                "score": hit.score,
            }
        )
    return expanded


def _cap_payload(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_chars = settings.kb_max_result_chars
    total = 0
    capped: list[dict[str, Any]] = []
    for item in results:
        content = item["content"]
        remaining = max_chars - total
        if remaining <= 0:
            break
        if len(content) > remaining:
            item = {**item, "content": content[:remaining] + "…"}
        total += len(item["content"])
        capped.append(item)
    return capped
