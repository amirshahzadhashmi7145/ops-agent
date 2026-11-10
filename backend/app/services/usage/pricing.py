"""Published list prices used to turn token usage into dollars.

Rates are USD per 1M tokens. Cached input is OpenAI automatic prefix caching
(typically 50% of input). Unknown models fall back to gpt-4o-mini.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

TWOPLACE = Decimal("0.01")
SIXPLACE = Decimal("0.000001")


@dataclass(frozen=True)
class ModelRates:
    input_per_million: Decimal
    output_per_million: Decimal
    cached_input_per_million: Decimal


# Snapshot for pricing strategy. Update when the vendor sheet changes.
_RATES: dict[str, ModelRates] = {
    "gpt-4o-mini": ModelRates(Decimal("0.150"), Decimal("0.600"), Decimal("0.075")),
    "gpt-4o": ModelRates(Decimal("2.50"), Decimal("10.00"), Decimal("1.25")),
    "gpt-4.1": ModelRates(Decimal("2.00"), Decimal("8.00"), Decimal("0.50")),
    "gpt-4.1-mini": ModelRates(Decimal("0.40"), Decimal("1.60"), Decimal("0.10")),
    "gpt-4.1-nano": ModelRates(Decimal("0.10"), Decimal("0.40"), Decimal("0.025")),
    "gpt-4.1-nano-2025-04-14": ModelRates(Decimal("0.10"), Decimal("0.40"), Decimal("0.025")),
    "o4-mini": ModelRates(Decimal("1.10"), Decimal("4.40"), Decimal("0.275")),
    "llama-3.3-70b-versatile": ModelRates(Decimal("0.59"), Decimal("0.79"), Decimal("0.59")),
    "gemini-2.0-flash": ModelRates(Decimal("0.10"), Decimal("0.40"), Decimal("0.025")),
    "gemini-2.5-flash": ModelRates(Decimal("0.15"), Decimal("0.60"), Decimal("0.0375")),
}

DEFAULT_RATES = _RATES["gpt-4o-mini"]
TARGET_GROSS_MARGIN = Decimal("0.75")


def rates_for(model: str) -> ModelRates:
    key = (model or "").strip().lower()
    if key in _RATES:
        return _RATES[key]
    for name, rates in _RATES.items():
        if name in key or key.startswith(name):
            return rates
    return DEFAULT_RATES


def _usd(prompt: int, completion: int, cached: int, rates: ModelRates) -> Decimal:
    uncached_prompt = max(prompt - cached, 0)
    cost = (
        Decimal(uncached_prompt) * rates.input_per_million
        + Decimal(cached) * rates.cached_input_per_million
        + Decimal(completion) * rates.output_per_million
    ) / Decimal(1_000_000)
    return cost.quantize(SIXPLACE, rounding=ROUND_HALF_UP)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0) -> Decimal:
    return _usd(prompt_tokens, completion_tokens, cached_tokens, rates_for(model))


def estimate_cost_without_cache(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    return _usd(prompt_tokens, completion_tokens, 0, rates_for(model))


def money(value: Decimal | float | int) -> float:
    return float(Decimal(value).quantize(SIXPLACE, rounding=ROUND_HALF_UP))


def display_money(value: Decimal | float | int) -> float:
    return float(Decimal(value).quantize(TWOPLACE, rounding=ROUND_HALF_UP))


def _pct(part: Decimal, whole: Decimal) -> float:
    if whole <= 0:
        return 0.0
    return float(((part / whole) * 100).quantize(TWOPLACE, rounding=ROUND_HALF_UP))


def _confidence(ticket_count: int) -> str:
    if ticket_count >= 50:
        return "high"
    if ticket_count >= 20:
        return "medium"
    return "low"


def recommend_pricing_model(
    *,
    ticket_count: int,
    mean_cost: Decimal,
    p50_cost: Decimal,
    p90_cost: Decimal,
    cache_hit_rate: Decimal,
    cv: Decimal,
) -> dict:
    """Pick a commercial model from measured ticket cost. No modeled fill-ins."""
    tail_ratio = (p90_cost / p50_cost) if p50_cost > 0 else Decimal("0")
    sample = "observed" if ticket_count >= 20 else ("thin" if ticket_count > 0 else "none")
    confidence = _confidence(ticket_count)

    labels = {
        "subscription": "Monthly subscription",
        "usage": "Usage-based",
        "hybrid": "Hybrid (seat + overage)",
        "per_ticket": "Per ticket",
    }

    if ticket_count == 0:
        return {
            "key": None,
            "label": "Need live tickets",
            "confidence": "low",
            "sample": sample,
            "why": [
                "No metered conversations in this window.",
                "Handle real tickets in Chat. This page only uses recorded LLM spend.",
            ],
            "signals": {
                "ticket_count": 0,
                "cost_cv": 0.0,
                "p90_vs_p50": 0.0,
                "cache_hit_rate_pct": 0.0,
            },
        }

    if cv < Decimal("0.45") and cache_hit_rate >= Decimal("0.25") and tail_ratio < Decimal("3"):
        key = "subscription"
        why = [
            f"Measured spread is {float(cv):.2f}; p90 is {float(tail_ratio):.1f}× median across {ticket_count} tickets.",
            f"Cache hit {float(cache_hit_rate * 100):.0f}% of calls, so a flat seat keeps margin.",
            "Customers prefer a known monthly bill when the mix does not swing.",
        ]
    elif cv > Decimal("0.9") or tail_ratio >= Decimal("4"):
        key = "usage"
        why = [
            f"Fat tail on live tickets: p90 {money(p90_cost)} vs median {money(p50_cost)}.",
            "Bill LLM cost plus markup so tool-heavy lookups do not sink a flat plan.",
            "Keep a small platform fee if you still want a subscription motion.",
        ]
    else:
        key = "hybrid"
        why = [
            f"Live mix is mixed (spread {float(cv):.2f}, p90 {float(tail_ratio):.1f}× median).",
            "A seat covers the cheap/cacheable half; overage covers SOP and tool tickets.",
            "That matches how support desks buy: predictable base, fair overflow.",
        ]

    return {
        "key": key,
        "label": labels[key],
        "confidence": confidence,
        "sample": sample,
        "why": why,
        "signals": {
            "ticket_count": ticket_count,
            "cost_cv": float(cv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "p90_vs_p50": float(tail_ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "cache_hit_rate_pct": _pct(cache_hit_rate, Decimal("1")),
        },
    }
