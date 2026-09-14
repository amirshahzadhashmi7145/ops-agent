from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ToolCallSummary(BaseModel):
    tool_name: str
    call_count: int
    success_count: int
    last_called_at: datetime | None = None


class ToolCallLogListItem(BaseModel):
    id: UUID
    tool_name: str
    source: str
    http_method: str | None
    response_status: int | None
    latency_ms: int | None
    success: bool
    created_by: str
    created_at: datetime
    conversation_id: UUID | None = None


class ToolCallLogDetail(ToolCallLogListItem):
    resource_id: UUID | None = None
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
