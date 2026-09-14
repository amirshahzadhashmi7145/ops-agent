import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProcessingStatus = Literal["queued", "formatting", "indexing", "ready", "failed"]


class ReferenceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    raw_text: str = Field(min_length=1)
    source_url: str | None = Field(default=None, max_length=2048)


class ReferenceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    raw_text: str | None = Field(default=None, min_length=1)
    source_url: str | None = Field(default=None, max_length=2048)


class ReferenceEnabledUpdate(BaseModel):
    enabled: bool


class ReferenceListItem(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None
    source_url: str | None
    enabled: bool
    processing_status: ProcessingStatus
    processing_error: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReferenceResponse(BaseModel):
    id: uuid.UUID
    title: str
    raw_text: str
    summary: str | None
    markdown: str | None
    content_hash: str
    source_url: str | None
    enabled: bool
    processing_status: ProcessingStatus
    processing_error: str | None
    embedding_model: str | None
    chunk_count: int = 0
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
