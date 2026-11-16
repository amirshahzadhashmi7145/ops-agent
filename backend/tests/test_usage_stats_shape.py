"""Pure usage stats aggregation shape (no DATABASE_URL)."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.usage.stats import _dec, _quantile, build_usage_stats_from_rows


def _event(
    *,
    cost: str = "0.01",
    without: str | None = None,
    prompt: int = 100,
    completion: int = 20,
    cached: int = 0,
    semantic_hit: bool = False,
    conversation_id=None,
    model: str = "gpt-4o-mini",
    day: str = "2026-01-10",
) -> SimpleNamespace:
    created = datetime.fromisoformat(f"{day}T12:00:00+00:00")
    cost_usd = Decimal(cost)
    return SimpleNamespace(
        cost_usd=cost_usd,
        cost_without_cache_usd=Decimal(without) if without is not None else cost_usd,
        prompt_tokens=prompt,
        completion_tokens=completion,
        cached_tokens=cached,
        semantic_hit=semantic_hit,
        conversation_id=conversation_id,
        model=model,
        created_at=created,
    )


def test_quantile_and_dec_helpers():
    assert _dec([]) == Decimal("0")
    assert _dec([Decimal("1"), Decimal("2")]) == Decimal("3")
    assert _quantile([], 0.5) == Decimal("0")
    assert _quantile([Decimal("10")], 0.9) == Decimal("10")
    assert _quantile([Decimal("1"), Decimal("2"), Decimal("3")], 0.5) == Decimal("2")


def test_usage_stats_empty_events_shape():
    hosting = {
        "monthly_usd": 40.0,
        "period_usd": 40.0,
        "days": 30,
        "items": [],
        "note": "test",
    }
    out = build_usage_stats_from_rows(
        [],
        days=30,
        hosting=hosting,
        cache_entries=(0, 0),
    )
    assert out["days"] == 30
    assert out["by_day"] == []
    assert out["tickets"]["conversations"] == 0
    assert out["tickets"]["observed"] is False
    assert out["tickets"]["avg_cost_usd"] == 0.0
    assert set(out["decision"]) >= {"key", "sample"}
    assert out["decision"]["key"] is None
    assert out["calls"]["total"] == 0
    assert out["spend_usd"] == 0.0


def test_usage_stats_synthetic_events_by_day_and_tickets():
    c1, c2 = uuid4(), uuid4()
    rows = [
        _event(cost="0.02", without="0.04", conversation_id=c1, day="2026-01-10"),
        _event(cost="0.01", without="0.01", conversation_id=c1, day="2026-01-10", cached=50),
        _event(cost="0.05", without="0.08", conversation_id=c2, day="2026-01-11"),
        _event(cost="0.00", without="0.00", semantic_hit=True, conversation_id=c2, day="2026-01-11"),
    ]
    hosting = {
        "monthly_usd": 10.0,
        "period_usd": 10.0,
        "days": 30,
        "items": [],
        "note": "test",
    }
    out = build_usage_stats_from_rows(
        rows,
        days=14,
        hosting=hosting,
        cache_entries=(3, 7),
        user_turns_by_conversation={c1: 2, c2: 4},
    )

    assert out["days"] == 14
    assert [day["day"] for day in out["by_day"]] == ["2026-01-10", "2026-01-11"]
    assert out["by_day"][0]["calls"] == 2
    assert out["by_day"][1]["calls"] == 2
    assert out["tickets"]["conversations"] == 2
    assert out["tickets"]["observed"] is True
    assert out["tickets"]["avg_user_turns"] == 3.0
    assert out["cache"]["entries"] == 3
    assert out["cache"]["lifetime_hits"] == 7
    assert out["decision"]["key"] in {"subscription", "hybrid", "usage", "per_ticket", None}
    assert "confidence" in out["decision"] or out["decision"]["key"] is None
    assert out["spend_usd"] > 0
    assert out["savings_usd"] > 0
