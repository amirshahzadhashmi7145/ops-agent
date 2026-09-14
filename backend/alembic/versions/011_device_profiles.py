"""device diagnostic profiles for connectivity and hardware SOPs

Revision ID: 011
Revises: 010
Create Date: 2026-07-09
"""

from typing import Sequence, Union
import json
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILES_PATH = Path(__file__).resolve().parents[2] / "app" / "data" / "device_profiles.json"


def upgrade() -> None:
    op.create_table(
        "sim_device_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment", sa.String(32), nullable=False, server_default="consumer"),
        sa.Column("camera_family", sa.String(32), nullable=False, server_default="connect"),
        sa.Column("model", sa.String(128), nullable=False, server_default=""),
        sa.Column("lookup_json", postgresql.JSONB(), nullable=True),
        sa.Column("classic_diagnostic_json", postgresql.JSONB(), nullable=True),
        sa.Column("health_json", postgresql.JSONB(), nullable=True),
        sa.Column("sim_triage_json", postgresql.JSONB(), nullable=True),
        sa.Column("sim_data_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["sim_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
    )

    bind = op.get_bind()
    customers = {
        row.email: row.id
        for row in bind.execute(sa.text("SELECT id, email FROM sim_customers")).fetchall()
    }

    new_devices = [
        ("NX-PRO-30001", customers.get("alex.rivera@example.com"), "Nexar Pro", "2025-08-15"),
        ("B2-MINI-50001", customers.get("jordan.lee@example.com"), "Beam2 mini", "2025-05-01"),
        ("NX-FLEET-90001", customers.get("sam.patel@example.com"), "Nexar One", "2025-02-01"),
    ]
    for serial, customer_id, model, purchase_date in new_devices:
        if not customer_id:
            continue
        existing = bind.execute(
            sa.text("SELECT id FROM sim_devices WHERE serial_number = :serial"),
            {"serial": serial},
        ).fetchone()
        if existing:
            device_id = existing[0]
        else:
            device_id = uuid.uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO sim_devices (id, customer_id, serial_number, model, status, purchase_date) "
                    "VALUES (:id, :customer_id, :serial, :model, 'active', :purchase_date)"
                ),
                {
                    "id": device_id,
                    "customer_id": customer_id,
                    "serial": serial,
                    "model": model,
                    "purchase_date": purchase_date,
                },
            )

        profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        profile = profiles.get(serial, {})
        bind.execute(
            sa.text(
                "INSERT INTO sim_device_profiles (id, device_id, segment, camera_family, model, lookup_json, "
                "classic_diagnostic_json, health_json, sim_triage_json, sim_data_json) VALUES ("
                ":id, :device_id, :segment, :camera_family, :model, CAST(:lookup_json AS jsonb), "
                "CAST(:classic_diagnostic_json AS jsonb), CAST(:health_json AS jsonb), "
                "CAST(:sim_triage_json AS jsonb), CAST(:sim_data_json AS jsonb))"
            ),
            {
                "id": uuid.uuid4(),
                "device_id": device_id,
                "segment": profile.get("segment", "consumer"),
                "camera_family": profile.get("camera_family", "connect"),
                "model": profile.get("model", model),
                "lookup_json": json.dumps(profile.get("lookup") or {}),
                "classic_diagnostic_json": json.dumps(profile.get("classic_diagnostic"))
                if profile.get("classic_diagnostic") is not None
                else None,
                "health_json": json.dumps(profile.get("health")) if profile.get("health") is not None else None,
                "sim_triage_json": json.dumps(profile.get("sim_triage"))
                if profile.get("sim_triage") is not None
                else None,
                "sim_data_json": json.dumps(profile.get("sim_data"))
                if profile.get("sim_data") is not None
                else None,
            },
        )

    # Seed profiles for existing devices
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    for serial in ["NX-BEAM-10001", "NX-ONE-20022", "NX-BEAM-10088"]:
        profile = profiles.get(serial)
        if not profile:
            continue
        row = bind.execute(
            sa.text("SELECT id FROM sim_devices WHERE serial_number = :serial"),
            {"serial": serial},
        ).fetchone()
        if not row:
            continue
        exists = bind.execute(
            sa.text("SELECT id FROM sim_device_profiles WHERE device_id = :device_id"),
            {"device_id": row[0]},
        ).fetchone()
        if exists:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO sim_device_profiles (id, device_id, segment, camera_family, model, lookup_json, "
                "classic_diagnostic_json, health_json, sim_triage_json, sim_data_json) VALUES ("
                ":id, :device_id, :segment, :camera_family, :model, CAST(:lookup_json AS jsonb), "
                "CAST(:classic_diagnostic_json AS jsonb), CAST(:health_json AS jsonb), "
                "CAST(:sim_triage_json AS jsonb), CAST(:sim_data_json AS jsonb))"
            ),
            {
                "id": uuid.uuid4(),
                "device_id": row[0],
                "segment": profile.get("segment", "consumer"),
                "camera_family": profile.get("camera_family", "connect"),
                "model": profile.get("model", serial),
                "lookup_json": json.dumps(profile.get("lookup") or {}),
                "classic_diagnostic_json": json.dumps(profile.get("classic_diagnostic"))
                if profile.get("classic_diagnostic") is not None
                else None,
                "health_json": json.dumps(profile.get("health")) if profile.get("health") is not None else None,
                "sim_triage_json": json.dumps(profile.get("sim_triage"))
                if profile.get("sim_triage") is not None
                else None,
                "sim_data_json": json.dumps(profile.get("sim_data"))
                if profile.get("sim_data") is not None
                else None,
            },
        )

    for slug, name, desc in [
        ("connectivity", "Connectivity", "Nexar Connect pairing and LTE connectivity"),
        ("hardware", "Hardware", "Hardware malfunction and warranty resolution"),
        ("classic-connectivity", "Classic Connectivity", "Nexar Classic app pairing and WiFi issues"),
    ]:
        op.execute(
            sa.text(
                "INSERT INTO sop_categories (id, slug, name, description) "
                "SELECT :id, :slug, :name, :desc "
                "WHERE NOT EXISTS (SELECT 1 FROM sop_categories WHERE slug = :slug)"
            ).bindparams(id=str(uuid.uuid4()), slug=slug, name=name, desc=desc)
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM sop_categories WHERE slug IN ('connectivity','hardware','classic-connectivity')"))
    op.drop_table("sim_device_profiles")
