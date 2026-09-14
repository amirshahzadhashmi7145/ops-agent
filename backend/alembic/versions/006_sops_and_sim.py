"""sop tables, simulation data, outbound messages

Revision ID: 006
Revises: 005
Create Date: 2026-07-08
"""

from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

sop_status = postgresql.ENUM(
    "queued", "formatting", "indexing", "ready", "failed",
    name="sopprocessingstatus", create_type=False,
)
sub_status = postgresql.ENUM(
    "active", "cancelled", "past_due", name="simsubscriptionstatus", create_type=False,
)
device_status = postgresql.ENUM(
    "active", "return_requested", "returned", "replaced",
    name="simdevicestatus", create_type=False,
)
tool_scope = postgresql.ENUM("internal", "external", name="toolscope", create_type=False)
connection_mode = postgresql.ENUM("direct", "existing", name="connectionmode", create_type=False)
http_method = postgresql.ENUM(
    "GET", "POST", "PUT", "PATCH", "DELETE", name="httpmethod", create_type=False,
)


def upgrade() -> None:
    for stmt in [
        """DO $$ BEGIN CREATE TYPE sopprocessingstatus AS ENUM ('queued','formatting','indexing','ready','failed'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
        """DO $$ BEGIN CREATE TYPE simsubscriptionstatus AS ENUM ('active','cancelled','past_due'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
        """DO $$ BEGIN CREATE TYPE simdevicestatus AS ENUM ('active','return_requested','returned','replaced'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
    ]:
        op.execute(stmt)

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sop_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "sop_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("processing_status", sop_status, nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("tool_warnings", postgresql.JSONB(), nullable=True),
        sa.Column("embedding_model", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["sop_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sop_processes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("process_key", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("trigger_phrases", postgresql.JSONB(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("tools", postgresql.JSONB(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["sop_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sop_process_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("process_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["sop_processes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # pgvector column via raw SQL (ARRAY used as placeholder above — replace)
    op.drop_column("sop_process_chunks", "embedding")
    op.execute("ALTER TABLE sop_process_chunks ADD COLUMN embedding vector(384)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sop_process_chunks_embedding "
        "ON sop_process_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "sim_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "sim_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_name", sa.String(128), nullable=False),
        sa.Column("status", sub_status, nullable=False),
        sa.Column("monthly_price_usd", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["sim_customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sim_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("serial_number", sa.String(128), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("status", device_status, nullable=False),
        sa.Column("purchase_date", sa.String(32), nullable=True),
        sa.Column("return_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["sim_customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("serial_number"),
    )
    op.create_table(
        "outbound_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_address", sa.String(255), nullable=False),
        sa.Column("to_address", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("related_entity_type", sa.String(64), nullable=True),
        sa.Column("related_entity_id", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed categories
    cat_sub = str(uuid.uuid4())
    cat_ret = str(uuid.uuid4())
    op.execute(
        sa.text(
            "INSERT INTO sop_categories (id, slug, name, description) VALUES "
            "(:id1, 'subscription', 'Subscription', 'Subscription management procedures'), "
            "(:id2, 'returns', 'Returns', 'Device return and RMA procedures')"
        ).bindparams(id1=cat_sub, id2=cat_ret)
    )

    # Seed sim customers
    c1, c2, c3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    op.execute(
        sa.text(
            "INSERT INTO sim_customers (id, email, full_name, phone) VALUES "
            "(:c1, 'alex.rivera@example.com', 'Alex Rivera', '+1-555-0101'), "
            "(:c2, 'jordan.lee@example.com', 'Jordan Lee', '+1-555-0102'), "
            "(:c3, 'sam.patel@example.com', 'Sam Patel', '+1-555-0103')"
        ).bindparams(c1=c1, c2=c2, c3=c3)
    )
    s1, s2, s3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    op.execute(
        sa.text(
            "INSERT INTO sim_subscriptions (id, customer_id, plan_name, status, monthly_price_usd) VALUES "
            "(:s1, :c1, 'Nexar Pro Monthly', 'active', '12.99'), "
            "(:s2, :c2, 'Nexar Basic Monthly', 'active', '7.99'), "
            "(:s3, :c3, 'Nexar Pro Annual', 'cancelled', '99.00')"
        ).bindparams(s1=s1, s2=s2, s3=s3, c1=c1, c2=c2, c3=c3)
    )
    d1, d2, d3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    op.execute(
        sa.text(
            "INSERT INTO sim_devices (id, customer_id, serial_number, model, status, purchase_date) VALUES "
            "(:d1, :c1, 'NX-BEAM-10001', 'Nexar Beam', 'active', '2025-03-12'), "
            "(:d2, :c1, 'NX-ONE-20022', 'Nexar One', 'active', '2024-11-02'), "
            "(:d3, :c2, 'NX-BEAM-10088', 'Nexar Beam', 'active', '2025-01-20')"
        ).bindparams(d1=d1, d2=d2, d3=d3, c1=c1, c2=c2)
    )

    # Seed internal resources for simulation APIs
    seed_user = "system@nexar.ops"
    tools = [
        ("lookup_customer_by_email", "Look up a simulated customer by email", "GET", "/api/sim/customers/{email}",
         '[{"name":"email","type":"string","required":true,"description":"Customer email","default_value":""}]'),
        ("list_subscriptions", "List subscriptions for a customer email", "GET", "/api/sim/subscriptions",
         '[{"name":"email","type":"string","required":true,"description":"Customer email","default_value":""}]'),
        ("cancel_subscription", "Cancel an active subscription and send confirmation message", "POST", "/api/sim/subscriptions/{subscription_id}/cancel",
         '[{"name":"subscription_id","type":"string","required":true,"description":"Subscription UUID","default_value":""},{"name":"reason","type":"string","required":false,"description":"Cancel reason","default_value":"Customer request"}]'),
        ("create_subscription", "Create a new subscription for a customer", "POST", "/api/sim/subscriptions",
         '[{"name":"email","type":"string","required":true,"description":"Customer email","default_value":""},{"name":"plan_name","type":"string","required":true,"description":"Plan name","default_value":"Nexar Pro Monthly"}]'),
        ("list_customer_devices", "List devices owned by a customer email", "GET", "/api/sim/devices",
         '[{"name":"email","type":"string","required":true,"description":"Customer email","default_value":""}]'),
        ("lookup_device", "Look up a device by serial number", "GET", "/api/sim/devices/{serial_number}",
         '[{"name":"serial_number","type":"string","required":true,"description":"Device serial","default_value":""}]'),
        ("initiate_return", "Start a device return and queue confirmation message", "POST", "/api/sim/devices/{serial_number}/return",
         '[{"name":"serial_number","type":"string","required":true,"description":"Device serial","default_value":""},{"name":"reason","type":"string","required":false,"description":"Return reason","default_value":"Customer return"}]'),
    ]
    for name, desc, method, path, params in tools:
        rid = str(uuid.uuid4())
        op.execute(
            sa.text(
                "INSERT INTO resources (id, name, description, tool_scope, connection_mode, connection_id, "
                "http_method, url, parameters, fixed_headers, active, last_tested_at, last_test_success, "
                "created_by, created_at, updated_at) VALUES ("
                ":id, :name, :desc, 'internal', 'direct', NULL, :method, :url, CAST(:params AS jsonb), "
                "'[]'::jsonb, true, now(), true, :user, now(), now())"
            ).bindparams(id=rid, name=name, desc=desc, method=method, url=path, params=params, user=seed_user)
        )


def downgrade() -> None:
    op.drop_table("outbound_messages")
    op.drop_table("sim_devices")
    op.drop_table("sim_subscriptions")
    op.drop_table("sim_customers")
    op.drop_table("sop_process_chunks")
    op.drop_table("sop_processes")
    op.drop_table("sop_documents")
    op.drop_table("sop_categories")
    bind = op.get_bind()
    sop_status.drop(bind, checkfirst=True)
    sub_status.drop(bind, checkfirst=True)
    device_status.drop(bind, checkfirst=True)
