"""Configured VM/hosting COGS for the Docker stack.

LLM spend is metered. Hosting is a monthly plan you set in env — not a
cloud bill scrape. Defaults match a single-box compose deploy: API +
local BGE embeddings + Next.js + Postgres/pgvector.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.core.config import settings
from app.services.usage.pricing import money

TWOPLACE = Decimal("0.01")


def _d(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def hosting_breakdown(*, days: int = 30) -> dict:
    items = [
        {
            "key": "compute",
            "label": "App VM (API + UI + local embeddings)",
            "specs": settings.hosting_compute_specs,
            "monthly_usd": money(_d(settings.hosting_compute_usd)),
            "note": "FastAPI, Next.js, and BGE embeddings on one box (CPU torch).",
        },
        {
            "key": "disk",
            "label": "Block storage (Postgres + model cache)",
            "specs": settings.hosting_disk_specs,
            "monthly_usd": money(_d(settings.hosting_disk_usd)),
            "note": "pgvector data volume + HuggingFace cache for BGE.",
        },
        {
            "key": "backups",
            "label": "Snapshots / backups",
            "specs": "daily snapshots",
            "monthly_usd": money(_d(settings.hosting_backup_usd)),
            "note": "DB + disk snapshots. Raise if you keep longer retention.",
        },
        {
            "key": "egress",
            "label": "Egress / bandwidth",
            "specs": settings.hosting_egress_specs,
            "monthly_usd": money(_d(settings.hosting_egress_usd)),
            "note": "Chat UI, tool webhooks, OpenAI calls leave the box.",
        },
    ]
    if _d(settings.hosting_other_usd) > 0:
        items.append(
            {
                "key": "other",
                "label": "Other hosting",
                "specs": settings.hosting_other_label or "misc",
                "monthly_usd": money(_d(settings.hosting_other_usd)),
                "note": "Extra managed services, monitoring, or CDN.",
            }
        )

    monthly = sum((_d(item["monthly_usd"]) for item in items), Decimal("0"))
    window = (monthly * Decimal(days) / Decimal(30)).quantize(TWOPLACE, rounding=ROUND_HALF_UP)
    capacity = max(int(settings.hosting_assumed_capacity_tickets), 1)
    at_capacity = (monthly / Decimal(capacity)).quantize(TWOPLACE, rounding=ROUND_HALF_UP)

    volumes = (200, 500, 2000, 8000)
    per_ticket = []
    for tickets in volumes:
        share = (monthly / Decimal(tickets)).quantize(TWOPLACE, rounding=ROUND_HALF_UP)
        per_ticket.append(
            {
                "tickets_per_month": tickets,
                "hosting_per_ticket_usd": money(share),
                "hosting_monthly_usd": money(monthly),
            }
        )

    return {
        "profile": settings.hosting_profile,
        "source": "configured",
        "currency": "USD",
        "provider_hint": settings.hosting_provider_hint,
        "line_items": items,
        "monthly_usd": money(monthly),
        "window_usd": float(window),
        "window_days": days,
        "assumed_capacity_tickets": capacity,
        "at_capacity_per_ticket_usd": money(at_capacity),
        "per_ticket_by_volume": per_ticket,
        "services": ["backend", "frontend", "db"],
    }
