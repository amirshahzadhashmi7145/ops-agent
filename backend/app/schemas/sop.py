import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SopCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class SopCategoryResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class SopProcessResponse(BaseModel):
    id: uuid.UUID
    process_key: str
    title: str
    description: str
    trigger_phrases: list[str]
    steps: list[dict[str, Any]]
    tools: list[str]
    sort_order: int

    model_config = {"from_attributes": True}


class SopDocumentCreate(BaseModel):
    title: str
    category_id: uuid.UUID
    raw_text: str


class SopDocumentUpdate(BaseModel):
    title: str
    category_id: uuid.UUID
    raw_text: str


class SopDocumentEnabledUpdate(BaseModel):
    enabled: bool


class SopDocumentListItem(BaseModel):
    id: uuid.UUID
    title: str
    category_id: uuid.UUID
    category_slug: str | None = None
    category_name: str | None = None
    summary: str | None
    enabled: bool
    processing_status: str
    processing_error: str | None
    process_count: int = 0
    tool_warnings: list[str] | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SopDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    category_id: uuid.UUID
    category_slug: str | None = None
    category_name: str | None = None
    raw_text: str
    summary: str | None
    markdown: str | None
    content_hash: str
    enabled: bool
    processing_status: str
    processing_error: str | None
    tool_warnings: list[str] | None = None
    embedding_model: str | None
    process_count: int = 0
    processes: list[SopProcessResponse] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
