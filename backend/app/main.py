from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent_rules import router as agent_rules_router
from app.api.agent_settings import router as agent_settings_router
from app.api.chat import router as chat_router
from app.api.kb import router as kb_router
from app.api.messages import router as messages_router
from app.api.resources import router as resources_router
from app.api.sim import router as sim_router
from app.api.device_ops import router as device_ops_router
from app.api.sops import router as sops_router
from app.core.config import settings
from app.services.internal_tools_seed import sync_internal_tools
from app.services.nexar_content_seed import sync_nexar_content

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        sync_internal_tools()
    except Exception:  # noqa: BLE001
        logger.exception("Internal tools sync skipped (DB may not be ready yet)")
    seed_task = asyncio.create_task(asyncio.to_thread(_seed_nexar_playbook))
    yield
    seed_task.cancel()


def _seed_nexar_playbook() -> None:
    uv_log = logging.getLogger("uvicorn.error")
    try:
        uv_log.info("Indexing Nexar knowledge base and SOPs...")
        counts = sync_nexar_content()
        uv_log.info("Nexar playbook ready: %s", counts)
    except Exception:  # noqa: BLE001
        logger.exception("Nexar playbook seed skipped (DB or embeddings may not be ready yet)")


app = FastAPI(title="Nexar Ops Agent API", version="0.1.0", lifespan=lifespan)

# Wildcard origins are never honored: this API uses credentialed requests, and
# "*" + credentials would expose every endpoint to any website.
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip() and o.strip() != "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Nexar-User"],
)

audit_logger = logging.getLogger("nexar.audit")
AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def audit_state_changes(request: Request, call_next):
    """Audit trail for every state-mutating request (incl. simulation endpoints):
    who did what, where, and with what outcome."""
    response = await call_next(request)
    if request.method in AUDITED_METHODS:
        audit_logger.info(
            "actor=%s method=%s path=%s status=%s",
            request.headers.get("X-Nexar-User", "anonymous"),
            request.method,
            request.url.path,
            response.status_code,
        )
    return response

app.include_router(resources_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(kb_router, prefix="/api")
app.include_router(agent_rules_router, prefix="/api")
app.include_router(agent_settings_router, prefix="/api")
app.include_router(sops_router, prefix="/api")
app.include_router(sim_router, prefix="/api")
app.include_router(device_ops_router, prefix="/api")
app.include_router(messages_router, prefix="/api")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
