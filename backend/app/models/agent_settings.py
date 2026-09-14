from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SETTINGS_ROW_ID = "default"


class AgentSettings(Base):
    """Singleton operator configuration for the agent runtime."""

    __tablename__ = "agent_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=SETTINGS_ROW_ID)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Nexar Ops Agent")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    greeting_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Hi! How can I help you today?",
    )
    escalation_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enable_kb_search: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_sop_matching: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_external_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_internal_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_tool_rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sop_auto_match_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    sop_match_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    kb_search_top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
