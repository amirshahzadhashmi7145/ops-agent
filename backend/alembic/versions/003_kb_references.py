"""knowledge base references and chunks with pgvector

Revision ID: 003
Revises: 002
Create Date: 2026-07-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

processing_status_enum = postgresql.ENUM(
    "queued",
    "formatting",
    "indexing",
    "ready",
    "failed",
    name="kbprocessingstatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE kbprocessingstatus AS ENUM (
                'queued', 'formatting', 'indexing', 'ready', 'failed'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "kb_references" not in inspector.get_table_names():
        op.create_table(
            "kb_references",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("raw_text", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("markdown", sa.Text(), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("source_url", sa.String(length=2048), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("processing_status", processing_status_enum, nullable=False, server_default="queued"),
            sa.Column("processing_error", sa.Text(), nullable=True),
            sa.Column("embedding_model", sa.String(length=255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_references_active ON kb_references (active)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_references_enabled ON kb_references (enabled)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_references_processing_status ON kb_references (processing_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_references_updated_at ON kb_references (updated_at)")

    if "kb_chunks" not in inspector.get_table_names():
        op.create_table(
            "kb_chunks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("heading_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["reference_id"], ["kb_references.id"], ondelete="CASCADE"),
        )
        op.execute("ALTER TABLE kb_chunks ADD COLUMN embedding vector(384)")
    else:
        chunk_columns = {column["name"] for column in inspector.get_columns("kb_chunks")}
        if "embedding" not in chunk_columns:
            op.execute("ALTER TABLE kb_chunks ADD COLUMN embedding vector(384)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_reference_id ON kb_chunks (reference_id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_kb_chunks_embedding
        ON kb_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_kb_chunks_embedding")
    op.drop_index("ix_kb_chunks_reference_id", table_name="kb_chunks")
    op.drop_table("kb_chunks")
    op.drop_index("ix_kb_references_updated_at", table_name="kb_references")
    op.drop_index("ix_kb_references_processing_status", table_name="kb_references")
    op.drop_index("ix_kb_references_enabled", table_name="kb_references")
    op.drop_index("ix_kb_references_active", table_name="kb_references")
    op.drop_table("kb_references")
    processing_status_enum.drop(op.get_bind(), checkfirst=True)
