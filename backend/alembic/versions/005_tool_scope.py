"""add tool_scope to resources

Revision ID: 005
Revises: 004
Create Date: 2026-07-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tool_scope_enum = postgresql.ENUM("internal", "external", name="toolscope", create_type=False)


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE toolscope AS ENUM ('internal', 'external');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.add_column(
        "resources",
        sa.Column(
            "tool_scope",
            tool_scope_enum,
            nullable=False,
            server_default="external",
        ),
    )


def downgrade() -> None:
    op.drop_column("resources", "tool_scope")
    bind = op.get_bind()
    tool_scope_enum.drop(bind, checkfirst=True)
