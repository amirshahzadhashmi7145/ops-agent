from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean, pstdev
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Message, MessageRole
from app.models.usage import LlmUsageEvent, SemanticCacheEntry
from app.services.usage.hosting import hosting_breakdown
from app.services.usage.pricing import (
    TARGET_GROSS_MARGIN,
    money,
    rates_for,
    recommend_pricing_model,
)

TWOPLACE = Decimal("0.01")
FOURPLACE = Decimal("0.0001")
MARKUP = Decimal("1") / (Decimal("1") - TARGET_GROSS_MARGIN)
INCLUDED_TICKETS = 1500


def _period_start(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _quantile(sorted_values: list[Decimal], q: float) -> Decimal:
    if not sorted_values:
        return Decimal("0")
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = min(len(sorted_values) - 1, max(0, int(round(q * (len(sorted_values) - 1)))))
    return sorted_values[index]


def _dec(values: Iterable[Decimal]) -> Decimal:
    return sum(values, Decimal("0"))


def usage_stats(db: Session, *, days: int = 30) -> dict:
    since = _period_start(days)
    rows = db.execute(select(LlmUsageEvent).where(LlmUsageEvent.created_at >= since)).scalars().all()

    spend = _dec(row.cost_usd for row in rows)
    without = _dec(row.cost_without_cache_usd for row in rows)
    saved = max(without - spend, Decimal("0"))
    prompt = sum(row.prompt_tokens for row in rows)
    completion = sum(row.completion_tokens for row in rows)
    cached = sum(row.cached_tokens for row in rows)
    llm_calls = sum(1 for row in rows if not row.semantic_hit)
    semantic_hits = sum(1 for row in rows if row.semantic_hit)
    prompt_cache_hits = sum(1 for row in rows if row.cached_tokens > 0)
    total_calls = llm_calls + semantic_hits
    cache_hit_rate = (Decimal(semantic_hits + prompt_cache_hits) / Decimal(total_calls)) if total_calls else Decimal("0")

    by_conversation: dict = defaultdict(lambda: Decimal("0"))
    calls_by_conversation: dict = defaultdict(int)
    tokens_by_conversation: dict = defaultdict(int)
    for row in rows:
        if not row.conversation_id:
            continue
        by_conversation[row.conversation_id] += row.cost_usd
        if not row.semantic_hit:
            calls_by_conversation[row.conversation_id] += 1
        tokens_by_conversation[row.conversation_id] += row.prompt_tokens + row.completion_tokens
    ticket_costs = sorted(by_conversation.values())
    ticket_count = len(ticket_costs)
    observed = ticket_count > 0
    mean_cost = (_dec(ticket_costs) / ticket_count) if ticket_count else Decimal("0")
    p50 = _quantile(ticket_costs, 0.5) if observed else Decimal("0")
    p90 = _quantile(ticket_costs, 0.9) if observed else Decimal("0")
    p99 = _quantile(ticket_costs, 0.99) if observed else Decimal("0")
    max_cost = ticket_costs[-1] if ticket_costs else Decimal("0")
    if ticket_count >= 2:
        floats = [float(value) for value in ticket_costs]
        spread = pstdev(floats) / mean(floats) if mean(floats) else 0.0
        cv = Decimal(str(round(spread, 4)))
    else:
        cv = Decimal("0")

    cheap = sum(1 for value in ticket_costs if value <= mean_cost * Decimal("0.5")) if observed else 0
    heavy = sum(1 for value in ticket_costs if value >= p90) if observed else 0

    user_turns: list[Decimal] = []
    if by_conversation:
        turn_rows = db.execute(
            select(Message.conversation_id, func.count(Message.id))
            .where(
                Message.conversation_id.in_(list(by_conversation.keys())),
                Message.role == MessageRole.user,
            )
            .group_by(Message.conversation_id)
        ).all()
        turns_map = {row[0]: int(row[1]) for row in turn_rows}
        user_turns = sorted(Decimal(turns_map.get(cid, 1)) for cid in by_conversation)
    avg_user_turns = (_dec(user_turns) / len(user_turns)) if user_turns else Decimal("0")
    p90_user_turns = _quantile(user_turns, 0.9) if user_turns else Decimal("0")
    max_user_turns = user_turns[-1] if user_turns else Decimal("0")
    call_counts = sorted(Decimal(calls_by_conversation.get(cid, 0)) for cid in by_conversation) if by_conversation else []
    token_counts = sorted(Decimal(tokens_by_conversation.get(cid, 0)) for cid in by_conversation) if by_conversation else []
    avg_llm_calls = (_dec(call_counts) / len(call_counts)) if call_counts else Decimal("0")
    avg_tokens = (_dec(token_counts) / len(token_counts)) if token_counts else Decimal("0")
    p90_tokens = _quantile(token_counts, 0.9) if token_counts else Decimal("0")
    cost_per_turn = (mean_cost / avg_user_turns) if avg_user_turns > 0 else Decimal("0")

    by_model: dict[str, dict] = {}
    for row in rows:
        bucket = by_model.setdefault(
            row.model or "unknown",
            {"model": row.model or "unknown", "calls": 0, "spend_usd": Decimal("0"), "tokens": 0},
        )
        bucket["calls"] += 1
        bucket["spend_usd"] += row.cost_usd
        bucket["tokens"] += row.prompt_tokens + row.completion_tokens

    by_day: dict[str, dict] = {}
    for row in rows:
        day = row.created_at.astimezone(timezone.utc).date().isoformat()
        bucket = by_day.setdefault(day, {"day": day, "spend_usd": Decimal("0"), "calls": 0, "saved_usd": Decimal("0")})
        bucket["spend_usd"] += row.cost_usd
        bucket["calls"] += 1
        bucket["saved_usd"] += max(row.cost_without_cache_usd - row.cost_usd, Decimal("0"))

    cache_entries = db.execute(
        select(func.count(SemanticCacheEntry.id), func.coalesce(func.sum(SemanticCacheEntry.hit_count), 0))
    ).one()

    hosting = hosting_breakdown(days=days)
    hosting_monthly = Decimal(str(hosting["monthly_usd"]))

    unit = (mean_cost * MARKUP).quantize(TWOPLACE, rounding=ROUND_HALF_UP)
    if mean_cost > 0 and unit < Decimal("0.01"):
        unit = Decimal("0.01")

    recommendation = recommend_pricing_model(
        ticket_count=ticket_count,
        mean_cost=mean_cost,
        p50_cost=p50,
        p90_cost=p90,
        cache_hit_rate=cache_hit_rate,
        cv=cv,
    )

    volumes = (200, 500, 2000, 8000)
    seat = Decimal("0")
    if observed:
        # Seat recovers fixed hosting + included LLM at target margin.
        seat = ((hosting_monthly + mean_cost * INCLUDED_TICKETS) * MARKUP).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        if seat < Decimal("1"):
            seat = Decimal("1")
    models = (
        _model_comparison(
            mean_cost=mean_cost,
            p90_cost=p90,
            unit=unit,
            seat=seat,
            hosting_monthly=hosting_monthly,
            volumes=volumes,
            avg_user_turns=avg_user_turns,
            p90_user_turns=p90_user_turns,
        )
        if observed
        else []
    )

    dominant_model = max(by_model.values(), key=lambda item: item["calls"])["model"] if by_model else "gpt-4o-mini"
    rates = rates_for(dominant_model)

    return {
        "days": days,
        "spend_usd": money(spend),
        "spend_without_optimizations_usd": money(without),
        "savings_usd": money(saved),
        "savings_pct": float(((saved / without) * 100).quantize(TWOPLACE, rounding=ROUND_HALF_UP)) if without else 0.0,
        "tokens": {
            "prompt": prompt,
            "completion": completion,
            "cached": cached,
            "total": prompt + completion,
        },
        "calls": {
            "llm": llm_calls,
            "semantic_hits": semantic_hits,
            "prompt_cache_hits": prompt_cache_hits,
            "total": total_calls,
        },
        "tickets": {
            "conversations": ticket_count,
            "avg_cost_usd": money(mean_cost),
            "p50_cost_usd": money(p50),
            "p90_cost_usd": money(p90),
            "p99_cost_usd": money(p99),
            "max_cost_usd": money(max_cost),
            "cv": float(cv),
            "cheap_share_pct": float(Decimal(cheap) / ticket_count * 100) if ticket_count else 0.0,
            "heavy_share_pct": float(Decimal(heavy) / ticket_count * 100) if ticket_count else 0.0,
            "observed": observed,
            "avg_user_turns": float(avg_user_turns.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "p90_user_turns": float(p90_user_turns),
            "max_user_turns": float(max_user_turns),
            "avg_llm_calls": float(avg_llm_calls.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "avg_tokens": int(avg_tokens),
            "p90_tokens": int(p90_tokens),
            "cost_per_user_turn_usd": money(cost_per_turn),
        },
        "cache": {
            "entries": int(cache_entries[0] or 0),
            "lifetime_hits": int(cache_entries[1] or 0),
            "hit_rate_pct": float((cache_hit_rate * 100).quantize(TWOPLACE, rounding=ROUND_HALF_UP)),
        },
        "by_model": [
            {
                "model": item["model"],
                "calls": item["calls"],
                "spend_usd": money(item["spend_usd"]),
                "tokens": item["tokens"],
            }
            for item in sorted(by_model.values(), key=lambda item: item["spend_usd"], reverse=True)
        ],
        "by_day": [
            {
                "day": item["day"],
                "spend_usd": money(item["spend_usd"]),
                "saved_usd": money(item["saved_usd"]),
                "calls": item["calls"],
            }
            for item in sorted(by_day.values(), key=lambda item: item["day"])
        ],
        "decision": recommendation,
        "hosting": hosting,
        "pricing": {
            "target_gross_margin_pct": float(TARGET_GROSS_MARGIN * 100),
            "suggested_price_per_ticket_usd": float(unit),
            "cost_per_ticket_usd": money(mean_cost),
            "usage_this_mix_per_ticket_usd": money(mean_cost * MARKUP),
            "usage_long_ticket_usd": money(p90 * MARKUP),
            "seat_usd": float(seat),
            "included_tickets": INCLUDED_TICKETS,
            "markup": float(MARKUP.quantize(Decimal("0.01"))),
            "models": models,
            "model_rates": {
                "model": dominant_model,
                "input_per_million_usd": float(rates.input_per_million),
                "output_per_million_usd": float(rates.output_per_million),
                "cached_input_per_million_usd": float(rates.cached_input_per_million),
            },
        },
    }


def _model_comparison(
    *,
    mean_cost: Decimal,
    p90_cost: Decimal,
    unit: Decimal,
    seat: Decimal,
    hosting_monthly: Decimal,
    volumes: tuple[int, ...],
    avg_user_turns: Decimal,
    p90_user_turns: Decimal,
) -> list[dict]:
    """Vendor margin at a few monthly volumes: measured LLM + fixed hosting."""
    included = INCLUDED_TICKETS
    overage = unit
    long_bill = p90_cost * MARKUP
    # Usage / per-ticket still need to recover hosting somehow — bake a floor
    # platform fee equal to hosting into the billed usage total at each volume.
    usage_platform = hosting_monthly * MARKUP

    def margin(revenue: Decimal, llm_cost: Decimal) -> float:
        if revenue <= 0:
            return 0.0
        cost = llm_cost + hosting_monthly
        return float(((revenue - cost) / revenue * 100).quantize(TWOPLACE, rounding=ROUND_HALF_UP))

    rows = []
    for key, label, blurb in (
        (
            "subscription",
            "Monthly subscription",
            f"${int(seat)}/seat/mo with {included:,} tickets included "
            f"(covers ${money(hosting_monthly)} hosting + LLM).",
        ),
        (
            "hybrid",
            "Hybrid (seat + overage)",
            f"${int(seat)}/seat includes {included:,} tickets, then {money(overage)} per extra ticket.",
        ),
        (
            "usage",
            "Usage-based",
            f"{float(MARKUP):.1f}× LLM for the whole thread "
            f"(avg {float(avg_user_turns):.1f} turns) + ${money(usage_platform)} platform "
            f"to cover hosting. Long ticket ({float(p90_user_turns):.0f} turns) "
            f"adds {money(long_bill)} LLM bill.",
        ),
        (
            "per_ticket",
            "Per ticket",
            f"{money(unit)} per resolved thread (LLM list). Hosting still sits as "
            f"${money(hosting_monthly)}/mo underneath.",
        ),
    ):
        scenarios = []
        for tickets in volumes:
            llm_cost = mean_cost * tickets
            if key == "subscription":
                customer = seat
            elif key == "hybrid":
                extra = max(tickets - included, 0)
                customer = seat + overage * extra
            elif key == "usage":
                customer = usage_platform + mean_cost * MARKUP * tickets
            else:
                customer = unit * tickets
            vendor_cost = llm_cost + hosting_monthly
            if key == "subscription":
                heavy_bill = seat
            elif key == "usage":
                heavy_bill = usage_platform + p90_cost * MARKUP * tickets
            elif key == "hybrid":
                heavy_bill = seat + max(tickets - included, 0) * max(overage, p90_cost * MARKUP)
            else:
                heavy_bill = customer
            scenarios.append(
                {
                    "tickets_per_month": tickets,
                    "customer_bill_usd": money(customer),
                    "vendor_cost_usd": money(vendor_cost),
                    "vendor_llm_usd": money(llm_cost),
                    "vendor_hosting_usd": money(hosting_monthly),
                    "vendor_margin_pct": margin(customer, llm_cost),
                    "heavy_customer_bill_usd": money(heavy_bill),
                }
            )
        rows.append({"key": key, "label": label, "summary": blurb, "scenarios": scenarios})
    return rows
