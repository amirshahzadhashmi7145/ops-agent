"""Request identity helpers.

Production: set REQUIRE_AUTH=true and OPS_API_KEYS to a comma-separated list of
Bearer tokens. Clients must send Authorization: Bearer <key> and X-Ops-User.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.config import settings


def _allowed_api_keys() -> set[str]:
    return {key.strip() for key in settings.ops_api_keys.split(",") if key.strip()}


def get_user_email(request: Request) -> str:
    x_ops_user = request.headers.get("X-Ops-User")
    authorization = request.headers.get("Authorization")

    if settings.require_auth:
        keys = _allowed_api_keys()
        if not keys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth is required but OPS_API_KEYS is not configured",
            )
        token = ""
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        if not token or token not in keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid Bearer token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not x_ops_user or not x_ops_user.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Ops-User header is required",
            )
        return x_ops_user.strip()[:320]

    return (x_ops_user or settings.dev_user_email).strip()[:320] or settings.dev_user_email
