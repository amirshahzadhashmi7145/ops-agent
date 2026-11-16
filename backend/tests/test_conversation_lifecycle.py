from types import SimpleNamespace

from app.models.conversation import ConversationStatus
from app.services.conversation_lifecycle import (
    apply_lifecycle_action,
    lifecycle_from_pipeline_trace,
    mark_ended,
    mark_escalated,
    mark_live,
)


def test_lifecycle_from_trace_resolve_and_escalate():
    assert lifecycle_from_pipeline_trace([]) is None
    assert lifecycle_from_pipeline_trace([{"type": "kb_search", "query": "x"}]) is None

    resolved = lifecycle_from_pipeline_trace(
        [
            {
                "type": "resource_result",
                "name": "ticketResolve",
                "success": True,
                "body": {"resolved": True, "reason": "Customer confirmed fixed"},
            }
        ]
    )
    assert resolved is not None
    assert resolved.status == "ended"
    assert resolved.source == "ticketResolve"
    assert "confirmed" in resolved.reason

    escalated = lifecycle_from_pipeline_trace(
        [
            {
                "type": "resource_result",
                "name": "ticketEscalate",
                "success": True,
                "body": {"escalated": True, "reason": "Safety concern"},
                "arguments": {"queue_parameters": "safety", "reason": "Safety concern"},
            }
        ]
    )
    assert escalated is not None
    assert escalated.status == "escalated"
    assert escalated.queue_parameters == "safety"

    # Last successful lifecycle tool wins.
    both = lifecycle_from_pipeline_trace(
        [
            {
                "type": "resource_result",
                "name": "ticketResolve",
                "success": True,
                "body": {"resolved": True, "reason": "done"},
            },
            {
                "type": "resource_result",
                "name": "ticketEscalate",
                "success": True,
                "body": {"escalated": True},
                "arguments": {"reason": "needs human"},
            },
        ]
    )
    assert both is not None
    assert both.status == "escalated"


def test_mark_helpers_set_reason_and_source():
    conv = SimpleNamespace(
        status=ConversationStatus.live,
        ended_at=None,
        status_reason=None,
        status_source=None,
    )
    mark_ended(conv, reason="Closed", source="ticketResolve")
    assert conv.status == ConversationStatus.ended
    assert conv.status_reason == "Closed"
    assert conv.status_source == "ticketResolve"
    assert conv.ended_at is not None

    mark_escalated(conv, reason="VIP", source="manual")
    assert conv.status == ConversationStatus.escalated
    assert conv.ended_at is None
    assert conv.status_source == "manual"

    mark_live(conv)
    assert conv.status == ConversationStatus.live
    assert conv.status_reason is None
    assert conv.status_source is None


def test_apply_lifecycle_action():
    conv = SimpleNamespace(
        status=ConversationStatus.live,
        ended_at=None,
        status_reason=None,
        status_source=None,
    )
    action = lifecycle_from_pipeline_trace(
        [
            {
                "type": "resource_result",
                "name": "ticketResolve",
                "success": True,
                "body": {"resolved": True, "reason": "Spam"},
            }
        ]
    )
    assert action is not None
    apply_lifecycle_action(conv, action)
    assert conv.status == ConversationStatus.ended
    assert conv.status_source == "ticketResolve"
