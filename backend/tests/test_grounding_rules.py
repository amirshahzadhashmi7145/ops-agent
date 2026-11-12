"""Static checks that the agent is configured to stay grounded."""

from app.services.agent_settings_defaults import DEFAULT_SYSTEM_PROMPT
from app.services.agent_runtime import PROMPT_INJECTION_GUARD
from app.services.grounding import looks_like_operational_action, needs_document_grounding
from app.services.usage.semantic_cache import cache_fingerprint


def test_docs_vs_ops_detectors_are_company_agnostic():
    # Docs / FAQ — force Articles, never auto-lock Workflow.
    assert needs_document_grounding(
        "What's the difference between Classic and Connect locks?"
    )
    assert needs_document_grounding("Can we create a Shopify RMA for an Amazon purchase?")
    assert needs_document_grounding("When should we escalate to a human queue?")
    assert needs_document_grounding("How do we handle LTE data issues on Connect locks?")
    assert needs_document_grounding("Tell me more about the out of warranty options.")
    assert needs_document_grounding(
        "According to policy, do we offer a MeridianVIP lifetime program?"
    )
    assert not looks_like_operational_action(
        "Can we create a Shopify RMA for an Amazon purchase?"
    )
    assert not looks_like_operational_action("How do we handle LTE data issues?")

    # Live ops — Workflow/tools OK.
    assert looks_like_operational_action(
        "Please cancel the subscription for customer alex.rivera@example.com"
    )
    assert looks_like_operational_action(
        "What is the health status of lock serial MD-GUARD-20022?"
    )
    assert looks_like_operational_action("Check SIM / LTE triage for MD-GUARD2-10088")
    assert looks_like_operational_action("Look up devices for alex.rivera@example.com")
    assert not needs_document_grounding(
        "Please cancel the subscription for customer alex.rivera@example.com"
    )


def test_cache_fingerprint_includes_corpus_version():
    assert cache_fingerprint(sop_process_id=None, greeting=False, corpus_version="abc") == (
        "mode:kb:c=abc"
    )
    assert cache_fingerprint(sop_process_id="p1", greeting=False, corpus_version="abc") == (
        "sop:p1:c=abc"
    )


def test_default_prompt_requires_kb_search_for_policy():
    prompt = DEFAULT_SYSTEM_PROMPT.lower()
    assert "search_knowledge_base" in prompt
    assert "never fabricate" in prompt
    assert "knowledge base" in prompt or "articles" in prompt
    assert "meridian customer support" not in prompt
    assert "company docs" in prompt


def test_default_prompt_requires_sop_before_ops_actions():
    prompt = DEFAULT_SYSTEM_PROMPT.lower()
    assert "search_sop_processes" in prompt
    assert "follow its steps" in prompt or "follow its steps exactly" in DEFAULT_SYSTEM_PROMPT


def test_default_prompt_forbids_narrating_search_without_tool_call():
    assert "NEVER say that you are going to search" in DEFAULT_SYSTEM_PROMPT
    assert "re-search first" in DEFAULT_SYSTEM_PROMPT.lower() or "re-search" in DEFAULT_SYSTEM_PROMPT


def test_security_preamble_blocks_invented_identifiers():
    assert "Never invent or alter customer identifiers" in PROMPT_INJECTION_GUARD


def test_playbook_has_groundable_content():
    from app.data.support_playbook import KB_ARTICLES, SOP_DOCUMENTS

    assert len(KB_ARTICLES) >= 8
    assert any(a["title"] == "Warranty Policy" for a in KB_ARTICLES)
    assert len(SOP_DOCUMENTS) >= 5
    assert any("Subscription" in d["title"] for d in SOP_DOCUMENTS)
