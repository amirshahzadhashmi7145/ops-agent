"""conversation status for live vs ended history

Revision ID: 016
Revises: 015
Create Date: 2026-11-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

conversation_status_enum = postgresql.ENUM(
    "live",
    "ended",
    name="conversationstatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE conversationstatus AS ENUM ('live', 'ended');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    conversation_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "conversations",
        sa.Column(
            "status",
            conversation_status_enum,
            nullable=False,
            server_default="live",
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_conversations_status", "conversations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_column("conversations", "ended_at")
    op.drop_column("conversations", "status")
    op.execute("DROP TYPE IF EXISTS conversationstatus")
