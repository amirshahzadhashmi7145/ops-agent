import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConnectionMode(str, enum.Enum):
    direct = "direct"
    existing = "existing"


class ToolScope(str, enum.Enum):
    internal = "internal"
    external = "external"


class HttpMethod(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ApiConnection(Base):
    __tablename__ = "api_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    default_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resources: Mapped[list["Resource"]] = relationship(back_populates="connection")


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_scope: Mapped[ToolScope] = mapped_column(
        ENUM(ToolScope, name="toolscope", create_type=False),
        nullable=False,
        default=ToolScope.external,
    )
    connection_mode: Mapped[ConnectionMode] = mapped_column(
        ENUM(ConnectionMode, name="connectionmode", create_type=False), nullable=False
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_connections.id"), nullable=True
    )
    http_method: Mapped[HttpMethod] = mapped_column(
        ENUM(HttpMethod, name="httpmethod", create_type=False), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    parameters: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    fixed_headers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    connection: Mapped[ApiConnection | None] = relationship(back_populates="resources")
    test_logs: Mapped[list["ResourceTestLog"]] = relationship(back_populates="resource")


class ResourceTestLog(Base):
    __tablename__ = "resource_test_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id"), nullable=True
    )
    request_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    response_status: Mapped[int | None] = mapped_column(nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resource: Mapped[Resource | None] = relationship(back_populates="test_logs")
