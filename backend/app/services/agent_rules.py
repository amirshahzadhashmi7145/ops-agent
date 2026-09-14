from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_rule import AgentRule

# Category value -> display heading, in the order they appear in the system prompt.
CATEGORY_ORDER: list[tuple[str, str]] = [
    ("business_context", "Business Context"),
    ("escalations", "Escalations"),
    ("response_tone_style", "Response Tone & Style"),
    ("agent_capabilities", "Agent Capabilities"),
]


def get_agent_rules(db: Session) -> list[AgentRule]:
    """All operator-defined rules, oldest first (stable authoring order)."""
    return list(db.execute(select(AgentRule).order_by(AgentRule.created_at.asc())).scalars().all())


def _category_value(category: object) -> str:
    return category.value if hasattr(category, "value") else str(category)


def format_agent_rules_prompt(rules: Iterable[AgentRule]) -> str:
    """Render operator-defined rules as a markdown block for the system prompt.

    Rules are grouped under their category headings in a fixed order, and each
    non-empty rule becomes a bullet. Categories with no rules are omitted, and an
    empty result (no rules at all) returns an empty string so nothing is appended.
    """
    grouped: dict[str, list[str]] = {}
    for rule in rules:
        content = (rule.content or "").strip()
        if not content:
            continue
        grouped.setdefault(_category_value(rule.category), []).append(content)

    sections: list[str] = []
    for value, heading in CATEGORY_ORDER:
        items = grouped.get(value)
        if not items:
            continue
        bullets = "\n".join(f"- {item}" for item in items)
        sections.append(f"## {heading}\n{bullets}")

    if not sections:
        return ""

    body = "\n\n".join(sections)
    return (
        "Operator-defined rules — you MUST follow all of these on every response, "
        "in addition to the rules above:\n\n"
        f"{body}"
    )
