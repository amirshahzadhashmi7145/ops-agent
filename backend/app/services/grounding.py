"""Company-agnostic grounding heuristics.

Production installs bring their own Articles/Workflows. These helpers must not
depend on Meridian (or any brand) keywords — only on intent shape:
informational/docs vs live operational action.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent_rule import AgentRule
from app.models.kb import KbReference
from app.models.sop import SopDocument

# Clear "do this now" / live-system intents. Safe to auto-match a Workflow.
_OPERATIONAL_ACTION = re.compile(
    r"\b("
    r"cancel|refund|escalate|look\s*up|lookup"
    r"|list (the )?(devices|subscriptions|orders|invoices)"
    r"|resend|reactivate|uplift|diagnose|triage"
    r"|create (a )?(ticket|return|rma|replacement|subscription|coupon|invoice)"
    r"|replace (the |my )?(lock|device|hardware|unit)"
    r"|return my|initiate.?return|ship (the |my )?"
    r"|change (the )?(address|plan|email|shipping)"
    r"|switch (to )?(monthly|annual)"
    r"|health status|order status|check (the )?(order|sim|subscription|device)"
    r"|pair(ing)? (the )?(keypad )?for"
    r")\b",
    re.IGNORECASE,
)

# How-to / policy phrasing — must NOT auto-lock a Workflow.
_HOWTO_PROCESS = re.compile(
    r"(?i)\b("
    r"how (do|should|can|does|to)"
    r"|when (do|should|can|does|to)"
    r"|what('?s| is| are) (the |our |a )?"
    r"|can we|do we|does (the |our )?"
    r"|is there|are there|should we"
    r"|difference between|compare |according to"
    r"|tell me (more )?about"
    r")\b"
)

_DOCS_SIGNAL = re.compile(
    r"(?i)\b("
    r"policy|policies|procedure|procedures|faq|guideline|guidelines"
    r"|coverage|warranty|warranties|sla|entitlement|program"
    r"|documentation|article|knowledge base|playbook"
    r")\b"
)

_LIVE_HANDLE = re.compile(
    r"(@[a-z0-9.-]+\.[a-z]{2,})"
    r"|(\bMD-[A-Z0-9-]+\b)"
    r"|(\bAC-[A-Z0-9-]+\b)"
    r"|(\b[A-Z]{2,}-\d{4,}\b)"
    r"|(\border\s*#?\s*\d{4,8}\b)"
    r"|(\b\d{6,8}\b)",
    re.IGNORECASE,
)

_FOLLOWUP = re.compile(
    r"(?i)^\s*(tell me more|and (then |the |what about)?|what about|why\??|go on)\b"
)


def looks_like_operational_action(text: str | None) -> bool:
    """True when the user is asking to perform / look up a live account or device action."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    # "How do we cancel subscriptions?" is docs. "Cancel for alex@…" is ops.
    if _HOWTO_PROCESS.search(cleaned) and not _LIVE_HANDLE.search(cleaned):
        return False
    if _OPERATIONAL_ACTION.search(cleaned):
        return True
    if _LIVE_HANDLE.search(cleaned) and re.search(
        r"(?i)\b(look|check|status|health|cancel|resend|list|devices|triage|sim|order)\b",
        cleaned,
    ):
        return True
    return False


def needs_document_grounding(text: str | None) -> bool:
    """True when the answer must come from Articles (not model memory / Workflow lock)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if looks_like_operational_action(cleaned):
        return False
    if _FOLLOWUP.search(cleaned):
        return True
    if _DOCS_SIGNAL.search(cleaned):
        return True
    if _HOWTO_PROCESS.search(cleaned):
        return True
    return False


def corpus_cache_version(db: Session) -> str:
    """Short digest of Articles/Workflows/Rules freshness so cache dies on content change."""

    def _stamp(model, *, enabled_only: bool = False) -> str:
        stmt = select(func.count(), func.max(model.updated_at))
        if enabled_only and hasattr(model, "enabled"):
            stmt = stmt.where(model.enabled.is_(True))
        row = db.execute(stmt).one()
        count = int(row[0] or 0)
        latest: datetime | None = row[1]
        ts = latest.isoformat() if latest else "none"
        return f"{count}:{ts}"

    raw = "|".join(
        [
            f"kb:{_stamp(KbReference, enabled_only=True)}",
            f"sop:{_stamp(SopDocument, enabled_only=True)}",
            f"rules:{_stamp(AgentRule)}",
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
