"""Static checks that the agent is configured to stay grounded."""

from app.services.agent_settings_defaults import DEFAULT_SYSTEM_PROMPT
from app.services.agent_runtime import SECURITY_PREAMBLE


def test_default_prompt_requires_kb_search_for_policy():
    prompt = DEFAULT_SYSTEM_PROMPT.lower()
    assert "search_knowledge_base" in prompt
    assert "never fabricate" in prompt
    assert "knowledge base" in prompt or "articles" in prompt


def test_default_prompt_requires_sop_before_ops_actions():
    prompt = DEFAULT_SYSTEM_PROMPT.lower()
    assert "search_sop_processes" in prompt
    assert "follow its steps" in prompt or "follow its steps exactly" in DEFAULT_SYSTEM_PROMPT


def test_default_prompt_forbids_narrating_search_without_tool_call():
    assert "NEVER say that you are going to search" in DEFAULT_SYSTEM_PROMPT
    assert "re-search first" in DEFAULT_SYSTEM_PROMPT.lower() or "re-search" in DEFAULT_SYSTEM_PROMPT


def test_security_preamble_blocks_invented_identifiers():
    assert "Never invent or alter customer identifiers" in SECURITY_PREAMBLE


def test_playbook_has_groundable_content():
    from app.data.support_playbook import KB_ARTICLES, SOP_DOCUMENTS

    assert len(KB_ARTICLES) >= 8
    assert any(a["title"] == "Warranty Policy" for a in KB_ARTICLES)
    assert len(SOP_DOCUMENTS) >= 5
    assert any("Subscription" in d["title"] for d in SOP_DOCUMENTS)
