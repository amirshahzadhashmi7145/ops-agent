from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tool_log import ToolCallLog
from app.schemas.tool_log import ToolCallLogDetail, ToolCallLogListItem, ToolCallSummary
from app.services.tool_log import list_tool_calls, summarize_tool_calls

router = APIRouter(prefix="/tool-logs", tags=["tool-logs"])


def _to_list_item(row: ToolCallLog) -> ToolCallLogListItem:
    return ToolCallLogListItem(
        id=row.id,
        tool_name=row.tool_name,
        source=row.source,
        http_method=row.http_method,
        response_status=row.response_status,
        latency_ms=row.latency_ms,
        success=row.success,
        created_by=row.created_by,
        created_at=row.created_at,
        conversation_id=row.conversation_id,
    )


def _to_detail(row: ToolCallLog) -> ToolCallLogDetail:
    return ToolCallLogDetail(
        **_to_list_item(row).model_dump(),
        resource_id=row.resource_id,
        request=row.request or {},
        response=row.response or {},
    )


@router.get("/summary", response_model=list[ToolCallSummary])
def tool_log_summary(db: Session = Depends(get_db)) -> list[ToolCallSummary]:
    return [ToolCallSummary(**item) for item in summarize_tool_calls(db)]


@router.get("", response_model=list[ToolCallLogListItem])
def list_logs(
    tool_name: str | None = Query(default=None),
    resource_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ToolCallLogListItem]:
    return [
        _to_list_item(row)
        for row in list_tool_calls(
            db,
            tool_name=tool_name,
            resource_id=resource_id,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/{log_id}", response_model=ToolCallLogDetail)
def get_log(log_id: UUID, db: Session = Depends(get_db)) -> ToolCallLogDetail:
    row = db.get(ToolCallLog, log_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tool call log not found")
    return _to_detail(row)
