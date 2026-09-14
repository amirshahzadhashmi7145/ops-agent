import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.resource import ApiConnection, ConnectionMode, HttpMethod, Resource, ResourceTestLog, ToolScope
from app.schemas.resource import (
    AppConfigResponse,
    ConnectionCreate,
    ConnectionResponse,
    ResourceCreate,
    ResourceListItem,
    ResourceResponse,
    ResourceTestRequest,
    ResourceTestResponse,
    ResourceUpdate,
)
from app.services.resource_executor import execute_resource_request, resolve_resource_url, resolve_test_headers
from app.services.tool_log import record_tool_call, redact_headers

router = APIRouter()

MAX_LOG_BODY = 10000


def get_user_email(request: Request) -> str:
    return request.headers.get("X-Nexar-User", settings.dev_user_email)


def _headers_to_json(headers: list) -> list[dict]:
    return [h.model_dump() if hasattr(h, "model_dump") else h for h in headers]


def _preview_for(resource: Resource) -> str:
    return resolve_resource_url(resource.tool_scope.value, resource.url)


def _to_list_item(resource: Resource) -> ResourceListItem:
    return ResourceListItem(
        id=resource.id,
        name=resource.name,
        description=resource.description,
        tool_scope=resource.tool_scope.value,
        http_method=resource.http_method.value,
        url=resource.url,
        last_tested_at=resource.last_tested_at,
        last_test_success=resource.last_test_success,
        active=resource.active,
        resolved_url_preview=_preview_for(resource),
    )


def _to_response(resource: Resource) -> ResourceResponse:
    return ResourceResponse(
        id=resource.id,
        name=resource.name,
        description=resource.description,
        tool_scope=resource.tool_scope.value,
        connection_mode=resource.connection_mode.value,
        connection_id=resource.connection_id,
        http_method=resource.http_method.value,
        url=resource.url,
        parameters=resource.parameters or [],
        fixed_headers=resource.fixed_headers or [],
        active=resource.active,
        last_tested_at=resource.last_tested_at,
        last_test_success=resource.last_test_success,
        created_by=resource.created_by,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
        resolved_url_preview=_preview_for(resource),
    )


def _get_connection(db: Session, connection_id: uuid.UUID | None) -> ApiConnection | None:
    if not connection_id:
        return None
    connection = db.get(ApiConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


async def _run_test(
    db: Session,
    payload: ResourceTestRequest,
    user_email: str,
    resource_id: uuid.UUID | None = None,
) -> ResourceTestResponse:
    connection = _get_connection(db, payload.connection_id)
    headers_for_test = resolve_test_headers(
        _headers_to_json(payload.fixed_headers),
        _headers_to_json(payload.test_headers) if payload.test_headers is not None else None,
    )
    result = await execute_resource_request(
        connection_mode=payload.connection_mode,
        url=payload.url,
        http_method=payload.http_method,
        connection=connection,
        fixed_headers=headers_for_test,
        payload=payload.test_payload,
        user_email=user_email,
        tool_scope=payload.tool_scope,
    )

    log = ResourceTestLog(
        resource_id=resource_id,
        request_snapshot={
            "tool_scope": payload.tool_scope,
            "connection_mode": payload.connection_mode,
            "url": payload.url,
            "http_method": payload.http_method,
            "test_payload": payload.test_payload,
            "test_headers": headers_for_test,
            "resolved_url": result.get("resolved_url"),
        },
        response_status=result.get("status_code"),
        response_body=str(result.get("body"))[:MAX_LOG_BODY] if result.get("body") is not None else None,
        latency_ms=result.get("latency_ms"),
        success=result.get("success", False),
        tested_by=user_email,
    )
    db.add(log)
    resource = db.get(Resource, resource_id) if resource_id else None
    record_tool_call(
        db,
        tool_name=resource.name if resource else payload.url,
        source="test",
        created_by=user_email,
        resource_id=resource_id,
        http_method=payload.http_method,
        request={
            "method": payload.http_method,
            "url": payload.url,
            "resolved_url": result.get("resolved_url"),
            "payload": payload.test_payload,
            "headers": redact_headers(
                {item.get("key"): item.get("value") for item in headers_for_test if item.get("key")}
            ),
        },
        response={
            "status_code": result.get("status_code"),
            "body": result.get("body"),
            "error": result.get("error"),
        },
        success=result.get("success", False),
        response_status=result.get("status_code"),
        latency_ms=result.get("latency_ms"),
    )

    if resource:
        resource.last_tested_at = datetime.now(timezone.utc)
        resource.last_test_success = result.get("success", False)

    db.commit()
    return ResourceTestResponse(**result)


@router.get("/config", response_model=AppConfigResponse)
def get_app_config() -> AppConfigResponse:
    return AppConfigResponse(internal_api_base_url=settings.internal_api_base_url)


@router.get("/connections", response_model=list[ConnectionResponse])
def list_connections(db: Session = Depends(get_db)) -> list[ConnectionResponse]:
    return db.query(ApiConnection).order_by(ApiConnection.created_at.desc()).all()


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
def create_connection(
    payload: ConnectionCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ConnectionResponse:
    connection = ApiConnection(
        name=payload.name,
        base_url=payload.base_url.rstrip("/"),
        default_headers=_headers_to_json(payload.default_headers),
        created_by=get_user_email(request),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.get("/resources", response_model=list[ResourceListItem])
def list_resources(db: Session = Depends(get_db)) -> list[ResourceListItem]:
    rows = db.query(Resource).order_by(Resource.updated_at.desc()).all()
    return [_to_list_item(row) for row in rows]


@router.post("/resources", response_model=ResourceResponse, status_code=201)
def create_resource(
    payload: ResourceCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ResourceResponse:
    if not payload.force_save and not payload.last_test_success:
        raise HTTPException(
            status_code=400,
            detail="Resource must pass a test before saving, or set force_save=true",
        )

    existing = db.query(Resource).filter(Resource.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Resource name already exists")

    connection = _get_connection(db, payload.connection_id)
    if payload.connection_mode == "existing" and not connection:
        raise HTTPException(status_code=400, detail="connection_id required for existing mode")

    resource = Resource(
        name=payload.name,
        description=payload.description,
        tool_scope=ToolScope(payload.tool_scope),
        connection_mode=ConnectionMode(payload.connection_mode),
        connection_id=payload.connection_id,
        http_method=HttpMethod(payload.http_method),
        url=payload.url,
        parameters=_headers_to_json(payload.parameters),
        fixed_headers=_headers_to_json(payload.fixed_headers),
        last_test_success=payload.last_test_success,
        last_tested_at=datetime.now(timezone.utc) if payload.last_test_success else None,
        created_by=get_user_email(request),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return _to_response(resource)


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: uuid.UUID, db: Session = Depends(get_db)) -> ResourceResponse:
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _to_response(resource)


@router.put("/resources/{resource_id}", response_model=ResourceResponse)
def update_resource(
    resource_id: uuid.UUID,
    payload: ResourceUpdate,
    db: Session = Depends(get_db),
) -> ResourceResponse:
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not payload.force_save and not payload.last_test_success:
        raise HTTPException(
            status_code=400,
            detail="Resource must pass a test before saving, or set force_save=true",
        )

    duplicate = (
        db.query(Resource)
        .filter(Resource.name == payload.name, Resource.id != resource_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Resource name already exists")

    _get_connection(db, payload.connection_id)

    resource.name = payload.name
    resource.description = payload.description
    resource.tool_scope = ToolScope(payload.tool_scope)
    resource.connection_mode = ConnectionMode(payload.connection_mode)
    resource.connection_id = payload.connection_id
    resource.http_method = HttpMethod(payload.http_method)
    resource.url = payload.url
    resource.parameters = _headers_to_json(payload.parameters)
    resource.fixed_headers = _headers_to_json(payload.fixed_headers)
    if payload.last_test_success:
        resource.last_test_success = payload.last_test_success
        resource.last_tested_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(resource)
    return _to_response(resource)


@router.patch("/resources/{resource_id}/active", response_model=ResourceResponse)
def set_resource_active(
    resource_id: uuid.UUID,
    payload: dict[str, bool],
    db: Session = Depends(get_db),
) -> ResourceResponse:
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    enabled = payload.get("active")
    if enabled is None:
        raise HTTPException(status_code=400, detail="active is required")

    resource.active = bool(enabled)
    db.commit()
    db.refresh(resource)
    return _to_response(resource)


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    resource = db.get(Resource, resource_id)
    if not resource or not resource.active:
        raise HTTPException(status_code=404, detail="Resource not found")
    resource.active = False
    db.commit()


@router.post("/resources/test", response_model=ResourceTestResponse)
async def test_resource_draft(
    payload: ResourceTestRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ResourceTestResponse:
    return await _run_test(db, payload, get_user_email(request))


@router.post("/resources/{resource_id}/test", response_model=ResourceTestResponse)
async def test_resource_saved(
    resource_id: uuid.UUID,
    payload: ResourceTestRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ResourceTestResponse:
    resource = db.get(Resource, resource_id)
    if not resource or not resource.active:
        raise HTTPException(status_code=404, detail="Resource not found")
    return await _run_test(db, payload, get_user_email(request), resource_id=resource_id)
