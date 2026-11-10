from decimal import Decimal
from types import SimpleNamespace

from app.services.llm.base import extract_token_usage
from app.services.usage.pricing import estimate_cost, estimate_cost_without_cache
from app.services.usage.semantic_cache import cache_fingerprint, query_is_cacheable


def test_extract_usage_reads_cached_tokens():
    usage = SimpleNamespace(
        prompt_tokens=1200,
        completion_tokens=80,
        total_tokens=1280,
        prompt_tokens_details=SimpleNamespace(cached_tokens=900),
    )
    out = extract_token_usage(usage)
    assert out["prompt_tokens"] == 1200
    assert out["cached_tokens"] == 900
    assert out["completion_tokens"] == 80


def test_extract_usage_missing_details():
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=4, total_tokens=14)
    out = extract_token_usage(usage)
    assert out["cached_tokens"] == 0


def test_prompt_cache_is_cheaper_than_full_input():
    full = estimate_cost_without_cache("gpt-4o-mini", 2000, 200)
    cached = estimate_cost("gpt-4o-mini", 2000, 200, cached_tokens=1500)
    assert cached < full
    assert cached > Decimal("0")


def test_volatile_queries_skip_semantic_cache():
    assert query_is_cacheable("What's our return policy for accessories?")
    assert not query_is_cacheable("Look up alex.rivera@example.com")
    assert not query_is_cacheable("Camera NX-BEAM-10088 has no LTE")
    assert not query_is_cacheable("hi")


def test_cache_fingerprint_namespaces_sops():
    assert cache_fingerprint(sop_process_id=None, greeting=True) == "mode:greeting"
    assert cache_fingerprint(sop_process_id="abc", greeting=False) == "sop:abc"
    assert cache_fingerprint(sop_process_id=None, greeting=False) == "mode:kb"


def test_recommend_none_when_no_tickets():
    from app.services.usage.pricing import recommend_pricing_model

    pick = recommend_pricing_model(
        ticket_count=0,
        mean_cost=Decimal("0"),
        p50_cost=Decimal("0"),
        p90_cost=Decimal("0"),
        cache_hit_rate=Decimal("0"),
        cv=Decimal("0"),
    )
    assert pick["key"] is None
    assert pick["sample"] == "none"


def test_recommend_hybrid_from_measured_mix():
    from app.services.usage.pricing import recommend_pricing_model

    pick = recommend_pricing_model(
        ticket_count=3,
        mean_cost=Decimal("0.004"),
        p50_cost=Decimal("0.003"),
        p90_cost=Decimal("0.01"),
        cache_hit_rate=Decimal("0.2"),
        cv=Decimal("0.5"),
    )
    assert pick["key"] == "hybrid"
    assert pick["confidence"] == "low"
    assert pick["sample"] == "thin"


def test_recommend_subscription_when_stable_and_cached():
    from app.services.usage.pricing import recommend_pricing_model

    pick = recommend_pricing_model(
        ticket_count=80,
        mean_cost=Decimal("0.003"),
        p50_cost=Decimal("0.0028"),
        p90_cost=Decimal("0.004"),
        cache_hit_rate=Decimal("0.4"),
        cv=Decimal("0.3"),
    )
    assert pick["key"] == "subscription"


def test_recommend_usage_when_tail_is_fat():
    from app.services.usage.pricing import recommend_pricing_model

    pick = recommend_pricing_model(
        ticket_count=80,
        mean_cost=Decimal("0.02"),
        p50_cost=Decimal("0.004"),
        p90_cost=Decimal("0.04"),
        cache_hit_rate=Decimal("0.1"),
        cv=Decimal("1.2"),
    )
    assert pick["key"] == "usage"


def test_hosting_breakdown_sums_line_items():
    from app.services.usage.hosting import hosting_breakdown

    out = hosting_breakdown(days=30)
    assert out["source"] == "configured"
    assert out["monthly_usd"] == sum(item["monthly_usd"] for item in out["line_items"])
    assert out["monthly_usd"] >= 48
    assert {item["key"] for item in out["line_items"]} >= {"compute", "disk", "backups", "egress"}
    assert out["per_ticket_by_volume"][0]["tickets_per_month"] == 200
