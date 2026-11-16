"""conversation escalated status + reason/source for AI close and handover

Revision ID: 017
Revises: 016
Create Date: 2026-11-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD VALUE must run outside a transaction on many Postgres versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE conversationstatus ADD VALUE IF NOT EXISTS 'escalated'")
    op.add_column("conversations", sa.Column("status_reason", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("status_source", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "status_source")
    op.drop_column("conversations", "status_reason")
    # Enum value removal is intentionally skipped (Postgres cannot drop enum values safely).
