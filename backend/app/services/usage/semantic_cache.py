import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.usage import LlmUsageEvent, SemanticCacheEntry
from app.services.embeddings.factory import get_embedding_provider
from app.services.usage.meter import record_llm_usage

# Live lookups (email, serial, order, phone) must never be served from cache.
_VOLATILE = re.compile(
    r"(@[a-z0-9.-]+\.[a-z]{2,})"
    r"|(\bNX-[A-Z0-9-]+\b)"
    r"|(\b[A-Z]{2,}\d{5,}\b)"
    r"|(\b\d{6,}\b)"
    r"|(\+?\d[\d\s().-]{8,}\d)",
    re.IGNORECASE,
)


def query_is_cacheable(text: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < 12:
        return False
    return _VOLATILE.search(cleaned) is None


def cache_fingerprint(*, sop_process_id: str | None, greeting: bool) -> str:
    if greeting:
        return "mode:greeting"
    if sop_process_id:
        return f"sop:{sop_process_id}"
    return "mode:kb"


def lookup_semantic_cache(
    db: Session,
    *,
    query: str,
    fingerprint: str,
) -> SemanticCacheEntry | None:
    if not settings.semantic_cache_enabled or not query_is_cacheable(query):
        return None
    try:
        vector = get_embedding_provider().embed_query(query)
    except Exception:  # noqa: BLE001
        return None
    now = datetime.now(timezone.utc)
    distance = SemanticCacheEntry.embedding.cosine_distance(vector)
    row = db.execute(
        select(SemanticCacheEntry, distance.label("distance"))
        .where(
            SemanticCacheEntry.fingerprint == fingerprint,
            SemanticCacheEntry.expires_at > now,
            SemanticCacheEntry.embedding.is_not(None),
        )
        .order_by("distance")
        .limit(1)
    ).first()
    if not row:
        return None
    entry, dist = row
    if float(dist) > settings.semantic_cache_max_distance:
        return None
    entry.hit_count += 1
    entry.last_hit_at = now
    db.commit()
    return entry


def store_semantic_cache(
    db: Session,
    *,
    query: str,
    fingerprint: str,
    response_text: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    if not settings.semantic_cache_enabled or not query_is_cacheable(query):
        return
    if not (response_text or "").strip():
        return
    try:
        vector = get_embedding_provider().embed_query(query)
    except Exception:  # noqa: BLE001
        return
    now = datetime.now(timezone.utc)
    db.add(
        SemanticCacheEntry(
            query_text=query.strip()[:4000],
            fingerprint=fingerprint,
            embedding=vector,
            response_text=response_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model or "",
            expires_at=now + timedelta(hours=settings.semantic_cache_ttl_hours),
        )
    )
    db.commit()


def record_semantic_hit(
    db: Session,
    entry: SemanticCacheEntry,
    *,
    conversation_id: UUID | None,
    user_email: str,
) -> None:
    record_llm_usage(
        db,
        model=entry.model,
        usage={"prompt_tokens": 0, "completion_tokens": 0, "cached_tokens": 0},
        purpose="semantic_hit",
        conversation_id=conversation_id,
        user_email=user_email,
        semantic_hit=True,
        avoided_prompt_tokens=entry.prompt_tokens,
        avoided_completion_tokens=entry.completion_tokens,
    )


def last_chat_usage(db: Session, conversation_id: UUID | None) -> LlmUsageEvent | None:
    if not conversation_id:
        return None
    return db.execute(
        select(LlmUsageEvent)
        .where(
            LlmUsageEvent.conversation_id == conversation_id,
            LlmUsageEvent.purpose.in_(("chat", "greeting")),
            LlmUsageEvent.semantic_hit.is_(False),
        )
        .order_by(LlmUsageEvent.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
