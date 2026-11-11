from contextlib import asynccontextmanager
import asyncio
import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.agent_rules import router as agent_rules_router
from app.api.agent_settings import router as agent_settings_router
from app.api.chat import router as chat_router
from app.api.kb import router as kb_router
from app.api.messages import router as messages_router
from app.api.tool_logs import router as tool_logs_router
from app.api.resources import router as resources_router
from app.api.sim import router as sim_router
from app.api.device_ops import router as device_ops_router
from app.api.sops import router as sops_router
from app.api.usage import router as usage_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.rate_limit import enforce_rate_limit
from app.services.internal_tools_seed import sync_internal_tools
from app.services.playbook_content_seed import sync_playbook_content

logger = logging.getLogger(__name__)


def _validate_production_settings() -> None:
    if settings.app_env.lower() != "production":
        return
    problems: list[str] = []
    if settings.allow_local_test:
        problems.append("ALLOW_LOCAL_TEST must be false in production")
    if "nexar:nexar@" in settings.database_url or settings.database_url.endswith("@db:5432/nexar_ops"):
        # Weak default credentials — still allow if password was changed in URL.
        if ":nexar@" in settings.database_url:
            problems.append("DATABASE_URL still uses the default nexar password")
    if settings.require_auth and not settings.ops_api_keys.strip():
        problems.append("REQUIRE_AUTH=true but OPS_API_KEYS is empty")
    if not settings.cors_origins.strip() or "*" in settings.cors_origins:
        problems.append("CORS_ORIGINS must be an explicit allowlist in production")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _validate_production_settings()
    try:
        sync_internal_tools()
    except Exception:  # noqa: BLE001
        logger.exception("Internal tools sync skipped (DB may not be ready yet)")
    seed_task = None
    if settings.seed_playbook_on_startup:
        seed_task = asyncio.create_task(asyncio.to_thread(_seed_playbook))
    yield
    if seed_task is not None:
        seed_task.cancel()


def _seed_playbook() -> None:
    uv_log = logging.getLogger("uvicorn.error")
    try:
        uv_log.info("Indexing knowledge base and workflows...")
        counts = sync_playbook_content()
        uv_log.info("Support playbook ready: %s", counts)
    except Exception:  # noqa: BLE001
        logger.exception("Support playbook seed skipped (DB or embeddings may not be ready yet)")


app = FastAPI(title="Ops Agent API", version="0.2.0", lifespan=lifespan)

# Wildcard origins are never honored: this API uses credentialed requests, and
# "*" + credentials would expose every endpoint to any website.
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip() and o.strip() != "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Ops-User", "X-Request-ID"],
)

audit_logger = logging.getLogger("ops.audit")
AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    path = request.url.path
    if path.startswith("/api/"):
        try:
            enforce_rate_limit(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers={"X-Request-ID": request_id},
            )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if request.method in AUDITED_METHODS:
        audit_logger.info(
            "request_id=%s actor=%s method=%s path=%s status=%s",
            request_id,
            request.headers.get("X-Ops-User", "anonymous"),
            request.method,
            path,
            response.status_code,
        )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, (StarletteHTTPException, RequestValidationError, HTTPException)):
        raise exc
    request_id = getattr(request.state, "request_id", "-")
    logger.exception("Unhandled error request_id=%s path=%s", request_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


app.include_router(resources_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(kb_router, prefix="/api")
app.include_router(agent_rules_router, prefix="/api")
app.include_router(agent_settings_router, prefix="/api")
app.include_router(sops_router, prefix="/api")
app.include_router(device_ops_router, prefix="/api")
app.include_router(sim_router, prefix="/api")
app.include_router(messages_router, prefix="/api")
app.include_router(tool_logs_router, prefix="/api")
app.include_router(usage_router, prefix="/api")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> JSONResponse:
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Readiness check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "down"},
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "database": "up",
            "app_env": settings.app_env,
            "require_auth": settings.require_auth,
            "allow_local_test": settings.allow_local_test,
        },
    )
