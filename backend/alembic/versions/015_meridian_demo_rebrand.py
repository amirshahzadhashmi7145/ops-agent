"""Rewrite demo sim data from camera brands to Meridian smart locks.

Revision ID: 015
Revises: 014
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SERIALS = [
    ("AC-APEX-30001", "MD-LATCH-30001", "Latch"),
    ("AC-SCOUT-10001", "MD-KEY-10001", "Key"),
    ("AC-HORIZON-20022", "MD-GUARD-20022", "Guard"),
    ("AC-SCOUT2-10088", "MD-GUARD2-10088", "Guard 2"),
    ("AC-MINI-50001", "MD-MINI-50001", "Guard Mini"),
    ("AC-FLEET-90001", "MD-FLEET-90001", "Guard"),
    ("NX-PRO-30001", "MD-LATCH-30001", "Latch"),
    ("NX-BEAM-10001", "MD-KEY-10001", "Key"),
    ("NX-ONE-20022", "MD-GUARD-20022", "Guard"),
    ("NX-BEAM-10088", "MD-GUARD2-10088", "Guard 2"),
    ("B2-MINI-50001", "MD-MINI-50001", "Guard Mini"),
    ("NX-FLEET-90001", "MD-FLEET-90001", "Guard"),
]

MODELS = [
    ("Scout Mini", "Guard Mini"),
    ("Scout 2", "Guard 2"),
    ("Scout", "Key"),
    ("Horizon", "Guard"),
    ("Apex", "Latch"),
    ("Beam2 mini", "Guard Mini"),
    ("Beam2", "Guard 2"),
    ("Beam", "Key"),
    ("One", "Guard"),
    ("Pro", "Latch"),
]

PLANS = [
    ("Apex Monthly", "Guard Monthly"),
    ("Apex Annual", "Guard Annual"),
    ("Pro Monthly", "Guard Monthly"),
    ("Pro Annual", "Guard Annual"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for old, new, model in SERIALS:
        conn.execute(
            sa.text(
                "UPDATE sim_devices SET serial_number = :new, model = :model "
                "WHERE serial_number = :old"
            ),
            {"old": old, "new": new, "model": model},
        )
    for old, new in MODELS:
        conn.execute(
            sa.text("UPDATE sim_devices SET model = :new WHERE model = :old"),
            {"old": old, "new": new},
        )
        conn.execute(
            sa.text("UPDATE sim_device_profiles SET model = :new WHERE model = :old"),
            {"old": old, "new": new},
        )
    for old, new in PLANS:
        conn.execute(
            sa.text("UPDATE sim_subscriptions SET plan_name = :new WHERE plan_name = :old"),
            {"old": old, "new": new},
        )
    for old_tag, new_tag in (("scout", "key"), ("horizon", "guard"), ("nexar-beam", "key"), ("nexar-one", "guard")):
        conn.execute(
            sa.text(
                "UPDATE sim_orders SET tags = REPLACE(tags::text, :old, :new)::jsonb "
                "WHERE tags::text LIKE :pattern"
            ),
            {"old": old_tag, "new": new_tag, "pattern": f"%{old_tag}%"},
        )


def downgrade() -> None:
    pass
