"""shipping fields on sim_orders for order shipping SOP

Revision ID: 010
Revises: 009
Create Date: 2026-07-09
"""

from typing import Sequence, Union
import uuid
from datetime import date, timedelta

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

fulfillment_status = postgresql.ENUM(
    "unfulfilled", "fulfilled", "cancelled", name="simfulfillmentstatus", create_type=False
)


def upgrade() -> None:
    op.execute(
        """DO $$ BEGIN CREATE TYPE simfulfillmentstatus AS ENUM ('unfulfilled','fulfilled','cancelled'); EXCEPTION WHEN duplicate_object THEN null; END $$;"""
    )

    op.add_column(
        "sim_orders",
        sa.Column("order_date", sa.String(32), nullable=False, server_default=""),
    )
    op.add_column(
        "sim_orders",
        sa.Column("fulfillment_status", fulfillment_status, nullable=False, server_default="unfulfilled"),
    )
    op.add_column("sim_orders", sa.Column("delivery_status", sa.String(64), nullable=True))
    op.add_column("sim_orders", sa.Column("deliver_by", sa.String(32), nullable=True))
    op.add_column("sim_orders", sa.Column("tags", postgresql.JSONB(), nullable=True))
    op.add_column("sim_orders", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    customers = bind.execute(sa.text("SELECT id, email, full_name FROM sim_customers")).fetchall()
    by_email = {row.email: (row.id, row.full_name) for row in customers}

    recent = (date.today() - timedelta(days=4)).isoformat()
    mid = (date.today() - timedelta(days=12)).isoformat()
    old = (date.today() - timedelta(days=45)).isoformat()
    deliver_soon = (date.today() + timedelta(days=3)).isoformat()
    deliver_past = (date.today() - timedelta(days=2)).isoformat()

    updates = {
        "346741": {
            "order_date": recent,
            "fulfillment_status": "fulfilled",
            "delivery_status": "IN_TRANSIT",
            "deliver_by": deliver_soon,
            "tags": '["nexar-one"]',
        },
        "353893": {
            "order_date": mid,
            "fulfillment_status": "fulfilled",
            "delivery_status": "IN_TRANSIT",
            "deliver_by": deliver_past,
            "tags": '["nexar-beam"]',
        },
        "320100": {
            "order_date": mid,
            "fulfillment_status": "fulfilled",
            "delivery_status": "DELIVERED",
            "deliver_by": mid,
            "tags": '["nexar-beam"]',
        },
        "250000": {
            "order_date": old,
            "fulfillment_status": "fulfilled",
            "delivery_status": "DELIVERED",
            "deliver_by": old,
            "tags": "[]",
        },
        "114-1536531-8448242": {
            "order_date": recent,
            "fulfillment_status": "fulfilled",
            "delivery_status": "IN_TRANSIT",
            "deliver_by": deliver_soon,
            "tags": "[]",
        },
    }

    for order_number, fields in updates.items():
        op.execute(
            sa.text(
                "UPDATE sim_orders SET order_date = :order_date, fulfillment_status = :fulfillment_status, "
                "delivery_status = :delivery_status, deliver_by = :deliver_by, tags = CAST(:tags AS jsonb) "
                "WHERE order_number = :order_number"
            ).bindparams(order_number=order_number, **fields)
        )

    alex = by_email.get("alex.rivera@example.com")
    jordan = by_email.get("jordan.lee@example.com")
    new_orders = []
    if alex:
        cid, name = alex
        new_orders.append(
            {
                "id": str(uuid.uuid4()),
                "customer_id": cid,
                "order_number": "410500",
                "channel": "shopify",
                "customer_email": "alex.rivera@example.com",
                "order_date": recent,
                "delivery_date": deliver_soon,
                "fulfillment_status": "unfulfilled",
                "delivery_status": None,
                "deliver_by": None,
                "tags": '["nexar-beam"]',
                "shipping_name": name,
                "shipping_line1": "742 Evergreen Terrace",
                "shipping_line2": "Apt 4B",
                "shipping_city": "Springfield",
                "shipping_state": "IL",
                "shipping_postal_code": "62704",
                "shipping_country": "US",
                "phone": "+1-555-0101",
            }
        )
    if jordan:
        cid, name = jordan
        new_orders.append(
            {
                "id": str(uuid.uuid4()),
                "customer_id": cid,
                "order_number": "410502",
                "channel": "shopify",
                "customer_email": "jordan.lee@example.com",
                "order_date": mid,
                "delivery_date": mid,
                "fulfillment_status": "fulfilled",
                "delivery_status": "DELIVERED",
                "deliver_by": mid,
                "tags": '["nexar-one"]',
                "tracking_number": "1Z999AA10123456784",
                "shipping_name": name,
                "shipping_line1": "88 Market Street",
                "shipping_line2": None,
                "shipping_city": "San Francisco",
                "shipping_state": "CA",
                "shipping_postal_code": "94105",
                "shipping_country": "US",
                "phone": "+1-555-0102",
            }
        )

    for order in new_orders:
        op.execute(
            sa.text(
                "INSERT INTO sim_orders (id, customer_id, order_number, channel, customer_email, order_date, "
                "delivery_date, fulfillment_status, delivery_status, deliver_by, tags, shipping_name, "
                "shipping_line1, shipping_line2, shipping_city, shipping_state, shipping_postal_code, "
                "shipping_country, phone, return_status, refund_status, tracking_number) VALUES ("
                ":id, :customer_id, :order_number, :channel, :customer_email, :order_date, :delivery_date, "
                ":fulfillment_status, :delivery_status, :deliver_by, CAST(:tags AS jsonb), :shipping_name, "
                ":shipping_line1, :shipping_line2, :shipping_city, :shipping_state, :shipping_postal_code, "
                ":shipping_country, :phone, 'none', 'none', :tracking_number)"
            ).bindparams(
                id=order["id"],
                customer_id=order["customer_id"],
                order_number=order["order_number"],
                channel=order["channel"],
                customer_email=order["customer_email"],
                order_date=order["order_date"],
                delivery_date=order["delivery_date"],
                fulfillment_status=order["fulfillment_status"],
                delivery_status=order["delivery_status"],
                deliver_by=order["deliver_by"],
                tags=order["tags"],
                shipping_name=order["shipping_name"],
                shipping_line1=order["shipping_line1"],
                shipping_line2=order["shipping_line2"],
                shipping_city=order["shipping_city"],
                shipping_state=order["shipping_state"],
                shipping_postal_code=order["shipping_postal_code"],
                shipping_country=order["shipping_country"],
                phone=order["phone"],
                tracking_number=order.get("tracking_number"),
            )
        )

    # shipping SOP category
    op.execute(
        sa.text(
            "INSERT INTO sop_categories (id, slug, name, description) "
            "SELECT :id, 'shipping', 'Shipping', 'Order shipping and delivery procedures' "
            "WHERE NOT EXISTS (SELECT 1 FROM sop_categories WHERE slug = 'shipping')"
        ).bindparams(id=str(uuid.uuid4()))
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM sim_orders WHERE order_number IN ('410500', '410502')"))
    op.drop_column("sim_orders", "cancelled_at")
    op.drop_column("sim_orders", "tags")
    op.drop_column("sim_orders", "deliver_by")
    op.drop_column("sim_orders", "delivery_status")
    op.drop_column("sim_orders", "fulfillment_status")
    op.drop_column("sim_orders", "order_date")
    bind = op.get_bind()
    fulfillment_status.drop(bind, checkfirst=True)
