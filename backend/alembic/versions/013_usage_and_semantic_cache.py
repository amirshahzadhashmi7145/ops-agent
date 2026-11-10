"""llm usage events and semantic response cache

Revision ID: 013
Revises: 012
Create Date: 2026-11-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("semantic_hit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("cost_without_cache_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_events_created_at", "llm_usage_events", ["created_at"])
    op.create_index("ix_llm_usage_events_purpose", "llm_usage_events", ["purpose"])
    op.create_index("ix_llm_usage_events_conversation_id", "llm_usage_events", ["conversation_id"])

    op.create_table(
        "semantic_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_semantic_cache_fingerprint", "semantic_cache", ["fingerprint"])
    op.create_index("ix_semantic_cache_expires_at", "semantic_cache", ["expires_at"])
    op.execute("ALTER TABLE semantic_cache ADD COLUMN embedding vector(384)")


def downgrade() -> None:
    op.drop_index("ix_semantic_cache_expires_at", table_name="semantic_cache")
    op.drop_index("ix_semantic_cache_fingerprint", table_name="semantic_cache")
    op.drop_table("semantic_cache")
    op.drop_index("ix_llm_usage_events_conversation_id", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_purpose", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_created_at", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")
