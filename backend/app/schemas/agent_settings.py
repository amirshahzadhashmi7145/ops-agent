from datetime import datetime

from pydantic import BaseModel, Field


class AgentSettingsRuntimeInfo(BaseModel):
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    env_max_tool_rounds: int
    env_sop_auto_match_threshold: float
    env_sop_match_threshold: float
    env_kb_search_top_k: int
    env_llm_temperature: float
    env_llm_max_tokens: int


class AgentSettingsResponse(BaseModel):
    id: str
    agent_name: str
    system_prompt: str
    greeting_message: str
    escalation_message: str
    enable_kb_search: bool
    enable_sop_matching: bool
    enable_external_tools: bool
    enable_internal_tools: bool
    max_tool_rounds: int | None
    sop_auto_match_threshold: float | None
    sop_match_threshold: float | None
    kb_search_top_k: int | None
    llm_temperature: float | None
    llm_max_tokens: int | None
    updated_by: str
    updated_at: datetime
    runtime: AgentSettingsRuntimeInfo

    model_config = {"from_attributes": True}


class AgentSettingsUpdate(BaseModel):
    agent_name: str = Field(min_length=1, max_length=255)
    system_prompt: str = Field(min_length=1)
    greeting_message: str = Field(min_length=1)
    escalation_message: str = ""
    enable_kb_search: bool = True
    enable_sop_matching: bool = True
    enable_external_tools: bool = True
    enable_internal_tools: bool = True
    max_tool_rounds: int | None = Field(default=None, ge=1, le=20)
    sop_auto_match_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    sop_match_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    kb_search_top_k: int | None = Field(default=None, ge=1, le=20)
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_max_tokens: int | None = Field(default=None, ge=256, le=8192)
