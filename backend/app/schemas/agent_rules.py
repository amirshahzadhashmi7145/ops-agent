import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AgentRuleCategory = Literal[
    "business_context",
    "escalations",
    "response_tone_style",
    "agent_capabilities",
]


class AgentRuleCreate(BaseModel):
    category: AgentRuleCategory
    content: str = Field(min_length=1, max_length=2000)


class AgentRuleUpdate(BaseModel):
    category: AgentRuleCategory | None = None
    content: str | None = Field(default=None, min_length=1, max_length=2000)


class AgentRuleResponse(BaseModel):
    id: uuid.UUID
    category: AgentRuleCategory
    content: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
