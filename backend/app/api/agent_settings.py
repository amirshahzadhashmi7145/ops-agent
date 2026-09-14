from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.agent_settings import AgentSettings
from app.schemas.agent_settings import (
    AgentSettingsResponse,
    AgentSettingsRuntimeInfo,
    AgentSettingsUpdate,
)
from app.services.agent_settings import get_agent_settings, runtime_model_info, touch_agent_settings

router = APIRouter()


def get_user_email(request: Request) -> str:
    return request.headers.get("X-Nexar-User", settings.dev_user_email)


def _to_response(agent: AgentSettings) -> AgentSettingsResponse:
    runtime = runtime_model_info()
    return AgentSettingsResponse(
        id=agent.id,
        agent_name=agent.agent_name,
        system_prompt=agent.system_prompt,
        greeting_message=agent.greeting_message,
        escalation_message=agent.escalation_message,
        enable_kb_search=agent.enable_kb_search,
        enable_sop_matching=agent.enable_sop_matching,
        enable_external_tools=agent.enable_external_tools,
        enable_internal_tools=agent.enable_internal_tools,
        max_tool_rounds=agent.max_tool_rounds,
        sop_auto_match_threshold=agent.sop_auto_match_threshold,
        sop_match_threshold=agent.sop_match_threshold,
        kb_search_top_k=agent.kb_search_top_k,
        llm_temperature=agent.llm_temperature,
        llm_max_tokens=agent.llm_max_tokens,
        updated_by=agent.updated_by,
        updated_at=agent.updated_at,
        runtime=AgentSettingsRuntimeInfo(
            llm_provider=runtime["llm_provider"],
            llm_model=runtime["llm_model"],
            embedding_provider=runtime["embedding_provider"],
            embedding_model=runtime["embedding_model"],
            env_max_tool_rounds=settings.agent_max_tool_rounds,
            env_sop_auto_match_threshold=settings.sop_auto_match_threshold,
            env_sop_match_threshold=settings.sop_match_threshold,
            env_kb_search_top_k=settings.kb_search_top_k,
            env_llm_temperature=settings.llm_temperature,
            env_llm_max_tokens=settings.llm_max_tokens,
        ),
    )


@router.get("/agent-settings", response_model=AgentSettingsResponse)
def read_agent_settings(db: Session = Depends(get_db)) -> AgentSettingsResponse:
    return _to_response(get_agent_settings(db))


@router.put("/agent-settings", response_model=AgentSettingsResponse)
def update_agent_settings(
    payload: AgentSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> AgentSettingsResponse:
    agent = get_agent_settings(db)
    agent.agent_name = payload.agent_name.strip()
    agent.system_prompt = payload.system_prompt.strip()
    agent.greeting_message = payload.greeting_message.strip()
    agent.escalation_message = payload.escalation_message.strip()
    agent.enable_kb_search = payload.enable_kb_search
    agent.enable_sop_matching = payload.enable_sop_matching
    agent.enable_external_tools = payload.enable_external_tools
    agent.enable_internal_tools = payload.enable_internal_tools
    agent.max_tool_rounds = payload.max_tool_rounds
    agent.sop_auto_match_threshold = payload.sop_auto_match_threshold
    agent.sop_match_threshold = payload.sop_match_threshold
    agent.kb_search_top_k = payload.kb_search_top_k
    agent.llm_temperature = payload.llm_temperature
    agent.llm_max_tokens = payload.llm_max_tokens
    touch_agent_settings(agent, get_user_email(request))
    db.commit()
    db.refresh(agent)
    return _to_response(agent)
