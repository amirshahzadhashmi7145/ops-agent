import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import case, desc, func, or_
from sqlalchemy.orm import Session

from app.models.resource import Resource
from app.models.tool_log import ToolCallLog

logger = logging.getLogger(__name__)

MAX_LOG_CHARS = 20000
BUILTIN_TOOLS = ("search_knowledge_base", "search_sop_processes")
_SECRET_HEADER_MARKERS = (
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "token",
    "secret",
    "password",
)


def redact_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in (headers or {}).items():
        lowered = str(key).lower()
        if any(marker in lowered for marker in _SECRET_HEADER_MARKERS):
            redacted[str(key)] = "***"
        else:
            redacted[str(key)] = str(value)
    return redacted


def clip_json(value: Any, *, max_chars: int = MAX_LOG_CHARS) -> Any:
    try:
        encoded = json.dumps(value, default=str)
    except TypeError:
        encoded = str(value)
    if len(encoded) <= max_chars:
        return value
    if isinstance(value, str):
        return value[:max_chars] + "\n...[truncated]"
    return {"_truncated": True, "preview": encoded[:max_chars]}


def record_tool_call(
    db: Session,
    *,
    tool_name: str,
    source: str,
    created_by: str,
    request: dict[str, Any],
    response: dict[str, Any],
    success: bool,
    resource_id: UUID | None = None,
    conversation_id: UUID | None = None,
    http_method: str | None = None,
    response_status: int | None = None,
    latency_ms: int | None = None,
) -> None:
    try:
        with db.begin_nested():
            db.add(
                ToolCallLog(
                    tool_name=tool_name,
                    source=source,
                    resource_id=resource_id,
                    conversation_id=conversation_id,
                    http_method=http_method,
                    request=clip_json(request) if isinstance(request, dict) else {"value": clip_json(request)},
                    response=clip_json(response) if isinstance(response, dict) else {"value": clip_json(response)},
                    response_status=response_status,
                    latency_ms=latency_ms,
                    success=success,
                    created_by=created_by,
                )
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to record tool call for %s", tool_name)


def summarize_tool_calls(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(
            ToolCallLog.tool_name,
            func.count(ToolCallLog.id).label("call_count"),
            func.sum(case((ToolCallLog.success.is_(True), 1), else_=0)).label("success_count"),
            func.max(ToolCallLog.created_at).label("last_called_at"),
        )
        .group_by(ToolCallLog.tool_name)
        .all()
    )
    by_name = {row.tool_name: row for row in rows}

    names: list[str] = list(BUILTIN_TOOLS)
    names.extend(name for (name,) in db.query(Resource.name).order_by(Resource.name.asc()).all())
    for extra in by_name:
        if extra not in names:
            names.append(extra)

    summaries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        row = by_name.get(name)
        summaries.append(
            {
                "tool_name": name,
                "call_count": int(row.call_count) if row else 0,
                "success_count": int(row.success_count or 0) if row else 0,
                "last_called_at": row.last_called_at if row else None,
            }
        )
    summaries.sort(key=lambda item: (-item["call_count"], item["tool_name"]))
    return summaries


def list_tool_calls(
    db: Session,
    *,
    tool_name: str | None = None,
    resource_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ToolCallLog]:
    query = db.query(ToolCallLog)
    if resource_id and tool_name:
        query = query.filter(or_(ToolCallLog.resource_id == resource_id, ToolCallLog.tool_name == tool_name))
    elif resource_id:
        query = query.filter(ToolCallLog.resource_id == resource_id)
    elif tool_name:
        query = query.filter(ToolCallLog.tool_name == tool_name)
    return (
        query.order_by(desc(ToolCallLog.created_at))
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 200))
        .all()
    )
