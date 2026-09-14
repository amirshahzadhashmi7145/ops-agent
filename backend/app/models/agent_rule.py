import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentRuleCategory(str, enum.Enum):
    business_context = "business_context"
    escalations = "escalations"
    response_tone_style = "response_tone_style"
    agent_capabilities = "agent_capabilities"


class AgentRule(Base):
    """A single operator-defined rule injected into the agent's system prompt."""

    __tablename__ = "agent_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[AgentRuleCategory] = mapped_column(
        ENUM(AgentRuleCategory, name="agentrulecategory", create_type=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
