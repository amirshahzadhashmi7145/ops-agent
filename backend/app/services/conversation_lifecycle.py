"""Detect and apply conversation close / human handover from agent tool results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.models.conversation import Conversation, ConversationStatus

StatusSource = Literal["ticketResolve", "ticketEscalate", "manual", "idle", "user"]

RESOLVE_TOOLS = frozenset({"ticketResolve"})
ESCALATE_TOOLS = frozenset({"ticketEscalate"})


@dataclass(frozen=True)
class LifecycleAction:
    status: Literal["ended", "escalated"]
    reason: str
    source: StatusSource
    queue_parameters: str | None = None


def _body_dict(body: Any) -> dict:
    if isinstance(body, dict):
        return body
    return {}


def lifecycle_from_pipeline_trace(trace: list[dict] | None) -> LifecycleAction | None:
    """Return the last successful resolve/escalate action in a turn's pipeline trace."""
    if not trace:
        return None
    action: LifecycleAction | None = None
    for event in trace:
        if event.get("type") != "resource_result" or not event.get("success"):
            continue
        name = str(event.get("name") or "")
        body = _body_dict(event.get("body"))
        if name in RESOLVE_TOOLS and body.get("resolved") is not False:
            reason = str(body.get("reason") or event.get("arguments", {}).get("reason") or "Resolved by assistant")
            action = LifecycleAction(status="ended", reason=reason, source="ticketResolve")
        elif name in ESCALATE_TOOLS and body.get("escalated") is not False:
            reason = str(
                body.get("reason")
                or (event.get("arguments") or {}).get("reason")
                or "Handed over to a human agent"
            )
            queue = (event.get("arguments") or {}).get("queue_parameters")
            action = LifecycleAction(
                status="escalated",
                reason=reason,
                source="ticketEscalate",
                queue_parameters=str(queue) if queue else None,
            )
    return action


def mark_live(conversation: Conversation) -> None:
    conversation.status = ConversationStatus.live
    conversation.ended_at = None
    conversation.status_reason = None
    conversation.status_source = None


def mark_ended(
    conversation: Conversation,
    *,
    reason: str | None = None,
    source: StatusSource = "manual",
    when: datetime | None = None,
) -> None:
    conversation.status = ConversationStatus.ended
    conversation.ended_at = when or datetime.now(timezone.utc)
    conversation.status_reason = (reason or "Conversation ended").strip() or "Conversation ended"
    conversation.status_source = source


def mark_escalated(
    conversation: Conversation,
    *,
    reason: str | None = None,
    source: StatusSource = "ticketEscalate",
) -> None:
    conversation.status = ConversationStatus.escalated
    conversation.ended_at = None
    conversation.status_reason = (reason or "Handed over to a human agent").strip() or "Handed over to a human agent"
    conversation.status_source = source


def apply_lifecycle_action(conversation: Conversation, action: LifecycleAction) -> None:
    if action.status == "ended":
        mark_ended(conversation, reason=action.reason, source=action.source)
    else:
        mark_escalated(conversation, reason=action.reason, source=action.source)
