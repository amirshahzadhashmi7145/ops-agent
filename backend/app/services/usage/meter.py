from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.usage import LlmUsageEvent
from app.services.llm.base import LLMResponse, extract_token_usage
from app.services.usage.pricing import estimate_cost, estimate_cost_without_cache


def record_llm_usage(
    db: Session | None,
    *,
    model: str,
    usage: dict[str, int] | None,
    purpose: str,
    conversation_id: UUID | None = None,
    user_email: str = "",
    semantic_hit: bool = False,
    avoided_prompt_tokens: int = 0,
    avoided_completion_tokens: int = 0,
) -> LlmUsageEvent:
    tokens = extract_token_usage(usage)
    prompt = tokens["prompt_tokens"]
    completion = tokens["completion_tokens"]
    cached = tokens["cached_tokens"]
    if semantic_hit:
        cost = Decimal("0")
        without = estimate_cost_without_cache(model, avoided_prompt_tokens, avoided_completion_tokens)
    else:
        cost = estimate_cost(model, prompt, completion, cached)
        without = estimate_cost_without_cache(model, prompt, completion)

    event = LlmUsageEvent(
        conversation_id=conversation_id,
        user_email=user_email or "",
        purpose=purpose,
        model=model or "",
        prompt_tokens=prompt,
        completion_tokens=completion,
        cached_tokens=cached,
        semantic_hit=semantic_hit,
        cost_usd=cost,
        cost_without_cache_usd=without,
    )
    owns = db is None
    session = db or SessionLocal()
    try:
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    except Exception:
        session.rollback()
        raise
    finally:
        if owns:
            session.close()


async def metered_chat(
    db: Session | None,
    provider: Any,
    messages: list,
    *,
    purpose: str,
    conversation_id: UUID | None = None,
    user_email: str = "",
    **kwargs: Any,
) -> LLMResponse:
    response: LLMResponse = await provider.chat(messages, **kwargs)
    record_llm_usage(
        db,
        model=response.model,
        usage=response.usage,
        purpose=purpose,
        conversation_id=conversation_id,
        user_email=user_email,
    )
    return response
