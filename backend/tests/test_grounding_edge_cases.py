"""Edge cases for company-agnostic grounding heuristics."""

from app.services.agent_runtime import PROMPT_INJECTION_GUARD
from app.services.grounding import looks_like_operational_action, needs_document_grounding


def test_invented_ticket_ids_are_not_operational_without_action_verbs():
    # Bare ticket-like tokens should not force Workflow/tools.
    assert not looks_like_operational_action("TKT-998877")
    assert not looks_like_operational_action("What about ticket 445566?")
    assert not needs_document_grounding("TKT-998877")


def test_faq_vs_operational_intent_boundaries():
    # FAQ / policy phrasing → Articles.
    faq_asks = [
        "What is our refund policy for annual seats?",
        "How do we handle escalation to a human queue?",
        "Can we create an RMA for marketplace purchases?",
        "What's the difference between Standard and Plus plans?",
        "According to policy, is lifetime coverage included?",
        "Tell me more about the warranty program.",
    ]
    for ask in faq_asks:
        assert needs_document_grounding(ask), ask
        assert not looks_like_operational_action(ask), ask

    # Live ops with handles → Workflow/tools OK.
    ops_asks = [
        "Cancel the subscription for customer ops.user@example.com",
        "Look up devices for ops.user@example.com",
        "Check order status for order 1234567",
        "What is the health status of lock serial AB-DEVICE-10001?",
        "Create a ticket for this outage and escalate",
    ]
    for ask in ops_asks:
        assert looks_like_operational_action(ask), ask
        assert not needs_document_grounding(ask), ask


def test_document_grounding_required_for_policy_questions():
    policy_asks = [
        "Do we offer a discount program for nonprofits?",
        "What coverage does the extended warranty include?",
        "Is there an SLA for priority support?",
        "Which entitlements apply after the trial ends?",
    ]
    for ask in policy_asks:
        assert needs_document_grounding(ask), ask


def test_howto_with_live_handle_stays_operational():
    # How-to phrasing normally docs, but a live handle unlocks ops.
    ask = "How do I check the health status of serial MD-LOCK-20022?"
    assert looks_like_operational_action(ask)
    assert not needs_document_grounding(ask)


def test_empty_and_followup_edges():
    assert not needs_document_grounding("")
    assert not looks_like_operational_action(None)
    assert needs_document_grounding("Tell me more")
    assert needs_document_grounding("What about prerequisites?")


def test_prompt_guard_forbids_invented_identifiers():
    assert "Never invent or alter customer identifiers" in PROMPT_INJECTION_GUARD
