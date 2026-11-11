"""Rewrite demo sim data from legacy brand serials to AetherCam.

Revision ID: 014
Revises: 013
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SERIALS = [
    ("NX-PRO-30001", "AC-APEX-30001", "Apex"),
    ("NX-BEAM-10001", "AC-SCOUT-10001", "Scout"),
    ("NX-ONE-20022", "AC-HORIZON-20022", "Horizon"),
    ("NX-BEAM-10088", "AC-SCOUT2-10088", "Scout 2"),
    ("B2-MINI-50001", "AC-MINI-50001", "Scout Mini"),
    ("NX-FLEET-90001", "AC-FLEET-90001", "Horizon"),
]

MODELS = [
    ("Nexar Beam", "Scout"),
    ("Nexar One", "Horizon"),
    ("Nexar Pro", "Apex"),
    ("Beam2 mini", "Scout Mini"),
    ("Beam2", "Scout 2"),
    ("Beam", "Scout"),
    ("One", "Horizon"),
    ("Pro", "Apex"),
]

PLANS = [
    ("Nexar Pro Monthly", "Apex Monthly"),
    ("Nexar Basic Monthly", "Basic Monthly"),
    ("Nexar Pro Annual", "Apex Annual"),
    ("Nexar Annual Plan", "Annual Plan"),
    ("Nexar Monthly Plan", "Monthly Plan"),
    ("Pro Monthly", "Apex Monthly"),
    ("Pro Annual", "Apex Annual"),
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
    conn.execute(
        sa.text(
            "UPDATE sim_orders SET rma_url = REPLACE(rma_url, 'returns.getnexar.com', 'returns.example.com') "
            "WHERE rma_url LIKE '%getnexar.com%'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE sim_orders SET tags = REPLACE(tags::text, 'nexar-beam', 'scout')::jsonb "
            "WHERE tags::text LIKE '%nexar-beam%'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE sim_orders SET tags = REPLACE(tags::text, 'nexar-one', 'horizon')::jsonb "
            "WHERE tags::text LIKE '%nexar-one%'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE agent_settings SET agent_name = 'Ops Agent' "
            "WHERE agent_name ILIKE '%nexar%'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE sop_categories SET description = REPLACE(description, 'Nexar ', '') "
            "WHERE description ILIKE '%nexar%'"
        )
    )


def downgrade() -> None:
    # Demo rebrand is one-way; restoring old brand names is intentionally unsupported.
    pass
