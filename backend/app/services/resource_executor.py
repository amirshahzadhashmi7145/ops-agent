import json
import os
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings
from app.core.url_safety import validate_outbound_url
from app.models.resource import ApiConnection

MAX_RESPONSE_BYTES = 256 * 1024
MAX_REDIRECTS = 3
_ENV_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def resolve_resource_url(tool_scope: str, url: str) -> str:
    """Resolve stored url/path into an absolute URL using env base for internal tools."""
    if tool_scope == "internal":
        path = url if url.startswith("/") else f"/{url}"
        return f"{settings.internal_api_base_url.rstrip('/')}{path}"
    return url


def build_resolved_url(
    connection_mode: str,
    url: str,
    connection: ApiConnection | None,
    payload: dict[str, Any],
    *,
    tool_scope: str = "external",
) -> str:
    if tool_scope == "internal":
        resolved = resolve_resource_url("internal", url)
    elif connection_mode == "existing":
        if not connection:
            raise ValueError("Connection is required for existing connection mode")
        base = connection.base_url.rstrip("/")
        path = url if url.startswith("/") else f"/{url}"
        resolved = f"{base}{path}"
    else:
        resolved = url

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in payload:
            raise ValueError(f"Missing URL parameter: {key}")
        return str(payload[key])

    return re.sub(r"\{(\w+)\}", replacer, resolved)


def merge_headers(
    connection: ApiConnection | None,
    fixed_headers: list[dict[str, Any]],
    user_email: str,
) -> dict[str, str]:
    headers: dict[str, str] = {"X-Nexar-User": user_email}

    if connection and connection.default_headers:
        for item in connection.default_headers:
            if isinstance(item, dict) and item.get("key"):
                headers[item["key"]] = str(item.get("value", ""))

    for item in fixed_headers:
        key = item.get("key", "")
        if not key:
            continue
        if item.get("is_secret"):
            secret = _resolve_secret_env(str(item.get("value", "")).strip())
            if secret:
                headers[key] = secret
        else:
            headers[key] = str(item.get("value", ""))

    return headers


def _resolve_secret_env(env_key: str) -> str | None:
    """Resolve a secret header value from the environment.

    Only env vars carrying the configured prefix may be referenced, so a
    resource definition can't be used to exfiltrate arbitrary process env
    (DATABASE_URL, provider API keys, ...) to an attacker-controlled URL.
    Missing or empty secrets are never sent as empty headers.
    """
    prefix = settings.resource_secret_env_prefix
    if not _ENV_KEY_PATTERN.match(env_key) or not env_key.startswith(prefix):
        return None
    return os.environ.get(env_key) or None


def resolve_test_headers(
    fixed_headers: list[dict[str, Any]],
    test_headers: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Inherit fixed headers; apply non-empty test header overrides on matching keys."""
    fixed = [item for item in fixed_headers if item.get("key")]
    if test_headers is None:
        return fixed

    overrides = [
        item
        for item in test_headers
        if item.get("key") and str(item.get("value", "")).strip()
    ]
    if not overrides:
        return fixed

    merged = {item["key"]: item for item in fixed}
    for item in overrides:
        merged[item["key"]] = item
    return list(merged.values())


def _validate_target(url: str, tool_scope: str) -> None:
    """Scope-aware target validation.

    Internal tools may only reach the configured internal API base (which is by
    construction our own service, so private-range checks don't apply); every
    other request must pass the full outbound SSRF validation.
    """
    if tool_scope == "internal":
        base = settings.internal_api_base_url.rstrip("/")
        if url != base and not url.startswith(f"{base}/"):
            raise ValueError("Internal tools may only call the internal API base URL")
        return
    validate_outbound_url(url)


def _truncate_body(content: bytes) -> str:
    if len(content) > MAX_RESPONSE_BYTES:
        return content[:MAX_RESPONSE_BYTES].decode("utf-8", errors="replace") + "\n...[truncated]"
    return content.decode("utf-8", errors="replace")


async def execute_resource_request(
    *,
    connection_mode: str,
    url: str,
    http_method: str,
    connection: ApiConnection | None,
    fixed_headers: list[dict[str, Any]],
    payload: dict[str, Any],
    user_email: str,
    tool_scope: str = "external",
) -> dict[str, Any]:
    resolved_url = build_resolved_url(
        connection_mode,
        url,
        connection,
        payload,
        tool_scope=tool_scope,
    )
    start = time.perf_counter()

    try:
        _validate_target(resolved_url, tool_scope)
    except ValueError as exc:
        return {
            "success": False,
            "status_code": None,
            "headers": {},
            "body": None,
            "latency_ms": 0,
            "error": f"Blocked request: {exc}",
            "resolved_url": resolved_url,
        }

    headers = merge_headers(connection, fixed_headers, user_email)

    method = http_method.upper()
    request_kwargs: dict[str, Any] = {"headers": headers, "timeout": 30.0}

    if method in {"POST", "PUT", "PATCH"}:
        request_kwargs["json"] = payload
    elif method == "GET" and payload:
        request_kwargs["params"] = payload

    try:
        # Redirects are followed manually: same-origin only, each hop re-validated,
        # so a 3xx from the target can't bounce the request (and its auth headers)
        # to an internal or attacker-chosen host.
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.request(method, resolved_url, **request_kwargs)
            for _ in range(MAX_REDIRECTS):
                if not response.is_redirect:
                    break
                location = response.headers.get("location")
                if not location:
                    break
                current = urlparse(str(response.request.url))
                next_url = urljoin(str(response.request.url), location)
                nxt = urlparse(next_url)
                if (nxt.scheme, nxt.hostname, nxt.port) != (
                    current.scheme,
                    current.hostname,
                    current.port,
                ):
                    break
                _validate_target(next_url, tool_scope)
                if response.status_code in {307, 308}:
                    response = await client.request(method, next_url, **request_kwargs)
                else:
                    response = await client.get(next_url, headers=headers, timeout=30.0)
        latency_ms = int((time.perf_counter() - start) * 1000)
        raw = response.content
        body_text = _truncate_body(raw)

        try:
            body: Any = json.loads(body_text)
        except json.JSONDecodeError:
            body = body_text

        success = 200 <= response.status_code < 300
        return {
            "success": success,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
            "latency_ms": latency_ms,
            "error": None if success else f"HTTP {response.status_code}",
            "resolved_url": resolved_url,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "success": False,
            "status_code": None,
            "headers": {},
            "body": None,
            "latency_ms": latency_ms,
            "error": str(exc),
            "resolved_url": resolved_url,
        }
