from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent_settings import SETTINGS_ROW_ID, AgentSettings
from app.models.resource import Resource, ToolScope
from app.services.agent_rules import format_agent_rules_prompt, get_agent_rules
from app.services.agent_settings_defaults import DEFAULT_GREETING, DEFAULT_SYSTEM_PROMPT


def get_agent_settings(db: Session) -> AgentSettings:
    row = db.get(AgentSettings, SETTINGS_ROW_ID)
    if row:
        return row

    row = AgentSettings(
        id=SETTINGS_ROW_ID,
        agent_name="Nexar Ops Agent",
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        greeting_message=DEFAULT_GREETING,
        escalation_message="",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def resolved_max_tool_rounds(agent: AgentSettings) -> int:
    if agent.max_tool_rounds is not None:
        return max(1, min(agent.max_tool_rounds, 20))
    return settings.agent_max_tool_rounds


def resolved_sop_auto_match_threshold(agent: AgentSettings) -> float:
    if agent.sop_auto_match_threshold is not None:
        return max(0.0, min(agent.sop_auto_match_threshold, 1.0))
    return settings.sop_auto_match_threshold


def resolved_sop_match_threshold(agent: AgentSettings) -> float:
    if agent.sop_match_threshold is not None:
        return max(0.0, min(agent.sop_match_threshold, 1.0))
    return settings.sop_match_threshold


def resolved_kb_search_top_k(agent: AgentSettings) -> int:
    if agent.kb_search_top_k is not None:
        return max(1, min(agent.kb_search_top_k, 20))
    return settings.kb_search_top_k


def resolved_llm_temperature(agent: AgentSettings) -> float:
    if agent.llm_temperature is not None:
        return max(0.0, min(agent.llm_temperature, 2.0))
    return settings.llm_temperature


def resolved_llm_max_tokens(agent: AgentSettings) -> int:
    if agent.llm_max_tokens is not None:
        return max(256, min(agent.llm_max_tokens, 8192))
    return settings.llm_max_tokens


def filter_resources_for_settings(resources: list[Resource], agent: AgentSettings) -> list[Resource]:
    filtered: list[Resource] = []
    for resource in resources:
        scope = getattr(resource.tool_scope, "value", resource.tool_scope)
        if scope == ToolScope.internal.value and not agent.enable_internal_tools:
            continue
        if scope == ToolScope.external.value and not agent.enable_external_tools:
            continue
        filtered.append(resource)
    return filtered


def build_system_prompt(db: Session, agent: AgentSettings) -> str:
    base = (agent.system_prompt or DEFAULT_SYSTEM_PROMPT).strip()
    if agent.agent_name.strip():
        base = base.replace("Nexar Ops Agent", agent.agent_name.strip(), 1)

    escalation = (agent.escalation_message or "").strip()
    if escalation:
        base = f"{base}\n\nEscalation guidance:\n{escalation}"

    rules_block = format_agent_rules_prompt(get_agent_rules(db))
    if rules_block:
        return f"{base}\n\n{rules_block}"
    return base


def runtime_model_info() -> dict[str, str]:
    provider = settings.llm_provider
    if provider == "gemini":
        model = settings.gemini_model
    elif provider == "openai":
        model = settings.openai_model
    else:
        model = settings.groq_model

    embedding_model = (
        settings.embedding_model_google
        if settings.embedding_provider == "google"
        else settings.embedding_model_local
    )
    return {
        "llm_provider": provider,
        "llm_model": model,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": embedding_model,
    }


def touch_agent_settings(agent: AgentSettings, user_email: str) -> None:
    agent.updated_by = user_email
    agent.updated_at = datetime.now(timezone.utc)
