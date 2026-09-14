"""Outbound URL validation (SSRF guard).

Lives in core with no model/service imports so both request schemas and the
resource executor can validate targets without pulling in the ORM layer.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import settings

ALLOWED_URL_SCHEMES = {"http", "https"}
# Names that must never be reachable regardless of what they resolve to.
BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata"}


def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_outbound_url(url: str, *, resolve_dns: bool = True) -> None:
    """Reject URLs that could reach internal or private network locations.

    Enforces http(s) scheme, forbids embedded credentials and blocked hostnames,
    and checks the target address — both IP literals and every DNS-resolved
    address — against private/loopback/link-local/reserved ranges. The address
    checks are bypassed only when settings.allow_local_test is enabled (dev).
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise ValueError(f"URL scheme '{parsed.scheme}' is not allowed")
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise ValueError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    if settings.allow_local_test:
        return
    if host in BLOCKED_HOSTS:
        raise ValueError(f"Requests to {host} are not allowed")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _is_forbidden_ip(literal):
            raise ValueError(f"Requests to {host} are not allowed")
        return

    if not resolve_dns:
        return
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host {host}") from exc
    for info in infos:
        if _is_forbidden_ip(ipaddress.ip_address(info[4][0])):
            raise ValueError(f"Requests to {host} are not allowed")
