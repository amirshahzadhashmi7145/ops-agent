from types import SimpleNamespace

from app.models.agent_rule import AgentRuleCategory
from app.services.agent_rules import format_agent_rules_prompt


def _rule(category, content):
    return SimpleNamespace(category=category, content=content)


def test_format_empty_returns_empty_string():
    assert format_agent_rules_prompt([]) == ""


def test_format_groups_by_category_in_fixed_order():
    rules = [
        _rule(AgentRuleCategory.response_tone_style, "Be concise."),
        _rule(AgentRuleCategory.business_context, "Orders ship in 2 days."),
        _rule(AgentRuleCategory.escalations, "Escalate fleet issues."),
        _rule(AgentRuleCategory.business_context, "We are US-only."),
        _rule(AgentRuleCategory.agent_capabilities, "You can check device status."),
    ]
    out = format_agent_rules_prompt(rules)

    # Fixed category order regardless of insertion order.
    assert out.index("## Business Context") < out.index("## Escalations")
    assert out.index("## Escalations") < out.index("## Response Tone & Style")
    assert out.index("## Response Tone & Style") < out.index("## Agent Capabilities")

    # Rules render as bullets under their heading.
    assert "- Orders ship in 2 days." in out
    assert "- We are US-only." in out
    assert "- Escalate fleet issues." in out
    assert "- Be concise." in out
    assert "- You can check device status." in out


def test_format_omits_empty_categories_and_blank_rules():
    rules = [
        _rule(AgentRuleCategory.business_context, "Real rule."),
        _rule(AgentRuleCategory.escalations, "   "),  # blank -> skipped
    ]
    out = format_agent_rules_prompt(rules)
    assert "## Business Context" in out
    assert "## Escalations" not in out
    assert "## Response Tone & Style" not in out


def test_format_accepts_plain_string_categories():
    # Robust to category arriving as a raw string (not the enum).
    rules = [_rule("business_context", "String category rule.")]
    out = format_agent_rules_prompt(rules)
    assert "## Business Context" in out
    assert "- String category rule." in out
