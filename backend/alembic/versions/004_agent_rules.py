"""agent rules injected into the system prompt

Revision ID: 004
Revises: 003
Create Date: 2026-07-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

agent_rule_category_enum = postgresql.ENUM(
    "business_context",
    "escalations",
    "response_tone_style",
    "agent_capabilities",
    name="agentrulecategory",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE agentrulecategory AS ENUM (
                'business_context', 'escalations', 'response_tone_style', 'agent_capabilities'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    agent_rule_category_enum.create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "agent_rules" not in inspector.get_table_names():
        op.create_table(
            "agent_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("category", agent_rule_category_enum, nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_by", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_rules_category ON agent_rules (category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_rules_created_at ON agent_rules (created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agent_rules_created_at")
    op.execute("DROP INDEX IF EXISTS ix_agent_rules_category")
    op.drop_table("agent_rules")
    agent_rule_category_enum.drop(op.get_bind(), checkfirst=True)
