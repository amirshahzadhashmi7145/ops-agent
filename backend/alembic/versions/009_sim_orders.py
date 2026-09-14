"""sim shopify orders for returns SOP

Revision ID: 009
Revises: 008
Create Date: 2026-07-09
"""

from typing import Sequence, Union
import uuid
from datetime import date, timedelta

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

order_channel = postgresql.ENUM("shopify", "amazon", name="simorderchannel", create_type=False)
return_status = postgresql.ENUM("none", "return_in_progress", "returned", name="simreturnstatus", create_type=False)
refund_status = postgresql.ENUM("none", "fully_refunded", name="simrefundstatus", create_type=False)


def upgrade() -> None:
    for stmt in [
        """DO $$ BEGIN CREATE TYPE simorderchannel AS ENUM ('shopify','amazon'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
        """DO $$ BEGIN CREATE TYPE simreturnstatus AS ENUM ('none','return_in_progress','returned'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
        """DO $$ BEGIN CREATE TYPE simrefundstatus AS ENUM ('none','fully_refunded'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
    ]:
        op.execute(stmt)

    op.create_table(
        "sim_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_number", sa.String(64), nullable=False),
        sa.Column("channel", order_channel, nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("delivery_date", sa.String(32), nullable=False),
        sa.Column("shipping_name", sa.String(255), nullable=False),
        sa.Column("shipping_line1", sa.String(255), nullable=False),
        sa.Column("shipping_line2", sa.String(255), nullable=True),
        sa.Column("shipping_city", sa.String(128), nullable=False),
        sa.Column("shipping_state", sa.String(64), nullable=False),
        sa.Column("shipping_postal_code", sa.String(32), nullable=False),
        sa.Column("shipping_country", sa.String(64), nullable=False, server_default="US"),
        sa.Column("phone", sa.String(64), nullable=False),
        sa.Column("return_status", return_status, nullable=False, server_default="none"),
        sa.Column("refund_status", refund_status, nullable=False, server_default="none"),
        sa.Column("return_reason", sa.String(128), nullable=True),
        sa.Column("rma_url", sa.String(512), nullable=True),
        sa.Column("tracking_number", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["sim_customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
    )

    bind = op.get_bind()
    customers = bind.execute(
        sa.text("SELECT id, email FROM sim_customers ORDER BY email")
    ).fetchall()
    by_email = {row.email: row.id for row in customers}
    if not by_email:
        return

    recent = (date.today() - timedelta(days=10)).isoformat()
    old = (date.today() - timedelta(days=45)).isoformat()
    mid = (date.today() - timedelta(days=20)).isoformat()

    orders = [
        {
            "id": str(uuid.uuid4()),
            "customer_id": by_email.get("alex.rivera@example.com"),
            "order_number": "346741",
            "channel": "shopify",
            "customer_email": "alex.rivera@example.com",
            "delivery_date": recent,
            "shipping_name": "Alex Rivera",
            "shipping_line1": "742 Evergreen Terrace",
            "shipping_line2": "Apt 4B",
            "shipping_city": "Springfield",
            "shipping_state": "IL",
            "shipping_postal_code": "62704",
            "shipping_country": "US",
            "phone": "+1-555-0101",
            "return_status": "none",
            "refund_status": "none",
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": by_email.get("jordan.lee@example.com"),
            "order_number": "353893",
            "channel": "shopify",
            "customer_email": "jordan.lee@example.com",
            "delivery_date": mid,
            "shipping_name": "Jordan Lee",
            "shipping_line1": "88 Market Street",
            "shipping_line2": None,
            "shipping_city": "San Francisco",
            "shipping_state": "CA",
            "shipping_postal_code": "94105",
            "shipping_country": "US",
            "phone": "+1-555-0102",
            "return_status": "return_in_progress",
            "refund_status": "none",
            "return_reason": "no_longer_needed",
            "rma_url": "https://returns.getnexar.com/rma/353893",
            "tracking_number": "9434650895206000059878",
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": by_email.get("sam.patel@example.com"),
            "order_number": "320100",
            "channel": "shopify",
            "customer_email": "sam.patel@example.com",
            "delivery_date": mid,
            "shipping_name": "Sam Patel",
            "shipping_line1": "1200 Lakeview Drive",
            "shipping_line2": None,
            "shipping_city": "Austin",
            "shipping_state": "TX",
            "shipping_postal_code": "78701",
            "shipping_country": "US",
            "phone": "+1-555-0103",
            "return_status": "returned",
            "refund_status": "fully_refunded",
            "return_reason": "changed_mind",
            "rma_url": "https://returns.getnexar.com/rma/320100",
            "tracking_number": "9400111899223197428490",
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": by_email.get("alex.rivera@example.com"),
            "order_number": "250000",
            "channel": "shopify",
            "customer_email": "alex.rivera@example.com",
            "delivery_date": old,
            "shipping_name": "Alex Rivera",
            "shipping_line1": "742 Evergreen Terrace",
            "shipping_line2": "Apt 4B",
            "shipping_city": "Springfield",
            "shipping_state": "IL",
            "shipping_postal_code": "62704",
            "shipping_country": "US",
            "phone": "+1-555-0101",
            "return_status": "none",
            "refund_status": "none",
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": by_email.get("jordan.lee@example.com"),
            "order_number": "114-1536531-8448242",
            "channel": "amazon",
            "customer_email": "jordan.lee@example.com",
            "delivery_date": recent,
            "shipping_name": "Jordan Lee",
            "shipping_line1": "88 Market Street",
            "shipping_line2": None,
            "shipping_city": "San Francisco",
            "shipping_state": "CA",
            "shipping_postal_code": "94105",
            "shipping_country": "US",
            "phone": "+1-555-0102",
            "return_status": "none",
            "refund_status": "none",
        },
    ]

    for order in orders:
        if not order["customer_id"]:
            continue
        op.execute(
            sa.text(
                "INSERT INTO sim_orders (id, customer_id, order_number, channel, customer_email, "
                "delivery_date, shipping_name, shipping_line1, shipping_line2, shipping_city, "
                "shipping_state, shipping_postal_code, shipping_country, phone, return_status, "
                "refund_status, return_reason, rma_url, tracking_number) VALUES ("
                ":id, :customer_id, :order_number, :channel, :customer_email, :delivery_date, "
                ":shipping_name, :shipping_line1, :shipping_line2, :shipping_city, :shipping_state, "
                ":shipping_postal_code, :shipping_country, :phone, :return_status, :refund_status, "
                ":return_reason, :rma_url, :tracking_number)"
            ).bindparams(
                id=order["id"],
                customer_id=order["customer_id"],
                order_number=order["order_number"],
                channel=order["channel"],
                customer_email=order["customer_email"],
                delivery_date=order["delivery_date"],
                shipping_name=order["shipping_name"],
                shipping_line1=order["shipping_line1"],
                shipping_line2=order["shipping_line2"],
                shipping_city=order["shipping_city"],
                shipping_state=order["shipping_state"],
                shipping_postal_code=order["shipping_postal_code"],
                shipping_country=order["shipping_country"],
                phone=order["phone"],
                return_status=order["return_status"],
                refund_status=order["refund_status"],
                return_reason=order.get("return_reason"),
                rma_url=order.get("rma_url"),
                tracking_number=order.get("tracking_number"),
            )
        )


def downgrade() -> None:
    op.drop_table("sim_orders")
    bind = op.get_bind()
    refund_status.drop(bind, checkfirst=True)
    return_status.drop(bind, checkfirst=True)
    order_channel.drop(bind, checkfirst=True)
