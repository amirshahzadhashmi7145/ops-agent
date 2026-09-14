import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.url_safety import validate_outbound_url

NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class ParameterSchema(BaseModel):
    name: str
    type: Literal["string", "number", "boolean"] = "string"
    required: bool = False
    description: str = ""
    default_value: str = ""


class HeaderSchema(BaseModel):
    key: str
    value: str
    is_secret: bool = False


class ConnectionCreate(BaseModel):
    name: str
    base_url: str
    default_headers: list[HeaderSchema] = Field(default_factory=list)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        url = value.strip()
        # Syntactic SSRF checks at save time; DNS-based checks run on every request.
        validate_outbound_url(url, resolve_dns=False)
        return url


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_url: str
    default_headers: list[dict[str, Any]]
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResourceBase(BaseModel):
    name: str
    description: str = ""
    tool_scope: Literal["internal", "external"] = "external"
    connection_mode: Literal["direct", "existing"] = "direct"
    connection_id: uuid.UUID | None = None
    http_method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    url: str
    parameters: list[ParameterSchema] = Field(default_factory=list)
    fixed_headers: list[HeaderSchema] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip().replace(" ", "_")
        if not NAME_PATTERN.match(normalized):
            raise ValueError("Name may only contain letters, numbers, underscores, and hyphens")
        return normalized

    @model_validator(mode="after")
    def validate_url_for_scope(self) -> "ResourceBase":
        url = self.url.strip()
        if self.tool_scope == "internal":
            if not url.startswith("/"):
                raise ValueError("Internal tools must use a path starting with /")
            self.connection_mode = "direct"
            self.connection_id = None
        elif self.connection_mode == "direct":
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("External tools require a full http(s) URL")
            # Syntactic SSRF checks at save time (scheme, credentials-in-URL,
            # blocked hosts, private IP literals); DNS-based checks run on every
            # request since {param} placeholders resolve at execution time.
            validate_outbound_url(url, resolve_dns=False)
        self.url = url
        return self


class ResourceCreate(ResourceBase):
    force_save: bool = False
    last_test_success: bool | None = None


class ResourceUpdate(ResourceBase):
    force_save: bool = False
    last_test_success: bool | None = None


class ResourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    tool_scope: str
    connection_mode: str
    connection_id: uuid.UUID | None
    http_method: str
    url: str
    parameters: list[dict[str, Any]]
    fixed_headers: list[dict[str, Any]]
    active: bool
    last_tested_at: datetime | None
    last_test_success: bool | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    resolved_url_preview: str | None = None

    model_config = {"from_attributes": True}


class ResourceListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    tool_scope: str
    http_method: str
    url: str
    last_tested_at: datetime | None
    last_test_success: bool | None
    active: bool
    resolved_url_preview: str | None = None

    model_config = {"from_attributes": True}


class ResourceTestRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    tool_scope: Literal["internal", "external"] = "external"
    connection_mode: Literal["direct", "existing"] = "direct"
    connection_id: uuid.UUID | None = None
    http_method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    url: str
    parameters: list[ParameterSchema] = Field(default_factory=list)
    fixed_headers: list[HeaderSchema] = Field(default_factory=list)
    test_payload: dict[str, Any] = Field(default_factory=dict)
    test_headers: list[HeaderSchema] | None = None


class ResourceTestResponse(BaseModel):
    success: bool
    status_code: int | None
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    latency_ms: int
    error: str | None = None
    resolved_url: str | None = None


class AppConfigResponse(BaseModel):
    internal_api_base_url: str
