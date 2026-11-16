"""Agent settings defaults and capability-flag filtering."""

from types import SimpleNamespace

from app.schemas.agent_settings import AgentSettingsUpdate
from app.services.agent_settings import filter_resources_for_settings
from app.services.agent_settings_defaults import DEFAULT_GREETING, DEFAULT_SYSTEM_PROMPT


def test_capability_flags_default_to_bools():
    # Schema defaults document the singleton enable_* booleans.
    defaults = AgentSettingsUpdate(
        agent_name="Ops Agent",
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        greeting_message=DEFAULT_GREETING,
    )
    assert defaults.enable_internal_tools is True
    assert defaults.enable_external_tools is True
    assert defaults.enable_kb_search is True
    assert defaults.enable_sop_matching is True
    assert isinstance(defaults.enable_internal_tools, bool)
    assert isinstance(defaults.enable_external_tools, bool)
    assert isinstance(defaults.enable_kb_search, bool)
    assert isinstance(defaults.enable_sop_matching, bool)


def test_default_prompt_and_greeting_are_non_empty():
    assert "Ops Agent" in DEFAULT_SYSTEM_PROMPT
    assert "search_knowledge_base" in DEFAULT_SYSTEM_PROMPT
    assert DEFAULT_GREETING.strip()


def test_filter_resources_respects_capability_flags():
    internal = SimpleNamespace(name="lookup_device", tool_scope="internal")
    external = SimpleNamespace(name="partner_api", tool_scope="external")
    resources = [internal, external]

    both = SimpleNamespace(
        enable_internal_tools=True,
        enable_external_tools=True,
    )
    assert filter_resources_for_settings(resources, both) == resources  # type: ignore[arg-type]

    no_internal = SimpleNamespace(
        enable_internal_tools=False,
        enable_external_tools=True,
    )
    assert filter_resources_for_settings(resources, no_internal) == [external]  # type: ignore[arg-type]

    no_external = SimpleNamespace(
        enable_internal_tools=True,
        enable_external_tools=False,
    )
    assert filter_resources_for_settings(resources, no_external) == [internal]  # type: ignore[arg-type]

    none = SimpleNamespace(
        enable_internal_tools=False,
        enable_external_tools=False,
    )
    assert filter_resources_for_settings(resources, none) == []  # type: ignore[arg-type]
