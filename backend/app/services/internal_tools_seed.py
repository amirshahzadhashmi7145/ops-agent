"""Ensure internal Tools & Resources stay in sync with code-owned JSON.

External tools live only in the database (lost on volume wipe).
Internal tools are defined in app/data/internal_tools.json and upserted on startup
(and can be re-run anytime), so a fresh DB still shows them in the UI.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.resource import ConnectionMode, HttpMethod, Resource, ToolScope

logger = logging.getLogger(__name__)

SEED_USER = "system@nexar.ops"
INTERNAL_TOOLS_PATH = Path(__file__).resolve().parent.parent / "data" / "internal_tools.json"


def load_internal_tool_defs() -> list[dict]:
    if not INTERNAL_TOOLS_PATH.exists():
        logger.warning("Internal tools JSON missing at %s", INTERNAL_TOOLS_PATH)
        return []
    return json.loads(INTERNAL_TOOLS_PATH.read_text(encoding="utf-8"))


def sync_internal_tools(db: Session | None = None) -> int:
    """Upsert every internal tool from JSON. Returns number of tools ensured."""
    owns_session = db is None
    session = db or SessionLocal()
    ensured = 0
    try:
        for item in load_internal_tool_defs():
            name = str(item["name"]).strip()
            if not name:
                continue
            existing = session.query(Resource).filter(Resource.name == name).first()
            params = item.get("parameters") or []
            if existing:
                existing.description = item.get("description") or existing.description
                existing.tool_scope = ToolScope.internal
                existing.connection_mode = ConnectionMode.direct
                existing.connection_id = None
                existing.http_method = HttpMethod(item["http_method"])
                existing.url = item["url"]
                existing.parameters = params
                existing.fixed_headers = existing.fixed_headers or []
                existing.active = True
                existing.created_by = existing.created_by or SEED_USER
            else:
                session.add(
                    Resource(
                        name=name,
                        description=item.get("description") or "",
                        tool_scope=ToolScope.internal,
                        connection_mode=ConnectionMode.direct,
                        connection_id=None,
                        http_method=HttpMethod(item["http_method"]),
                        url=item["url"],
                        parameters=params,
                        fixed_headers=[],
                        active=True,
                        last_test_success=True,
                        created_by=SEED_USER,
                    )
                )
            ensured += 1
        session.commit()
        logger.info("Synced %s internal tools from %s", ensured, INTERNAL_TOOLS_PATH.name)
        return ensured
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("Failed to sync internal tools")
        raise
    finally:
        if owns_session:
            session.close()
