"""agent settings singleton for runtime configuration

Revision ID: 008
Revises: 007
Create Date: 2026-07-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.agent_settings_defaults import DEFAULT_GREETING, DEFAULT_SYSTEM_PROMPT

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "agent_settings" not in inspector.get_table_names():
        op.create_table(
            "agent_settings",
            sa.Column("id", sa.String(length=32), primary_key=True),
            sa.Column("agent_name", sa.String(length=255), nullable=False),
            sa.Column("system_prompt", sa.Text(), nullable=False),
            sa.Column("greeting_message", sa.Text(), nullable=False),
            sa.Column("escalation_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("enable_kb_search", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("enable_sop_matching", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("enable_external_tools", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("enable_internal_tools", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("max_tool_rounds", sa.Integer(), nullable=True),
            sa.Column("sop_auto_match_threshold", sa.Float(), nullable=True),
            sa.Column("sop_match_threshold", sa.Float(), nullable=True),
            sa.Column("kb_search_top_k", sa.Integer(), nullable=True),
            sa.Column("llm_temperature", sa.Float(), nullable=True),
            sa.Column("llm_max_tokens", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.String(length=255), nullable=False, server_default="system"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO agent_settings (
                id, agent_name, system_prompt, greeting_message, escalation_message, updated_by
            )
            VALUES (
                'default', 'Nexar Ops Agent', :system_prompt, :greeting_message, '', 'system'
            )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"system_prompt": DEFAULT_SYSTEM_PROMPT, "greeting_message": DEFAULT_GREETING},
    )


def downgrade() -> None:
    op.drop_table("agent_settings")
