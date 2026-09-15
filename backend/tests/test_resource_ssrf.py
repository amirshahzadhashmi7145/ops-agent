import pytest

from app.core.config import settings
from app.core.url_safety import validate_outbound_url
from app.schemas.resource import ConnectionCreate, ResourceCreate
from app.services.resource_executor import execute_resource_request, merge_headers


@pytest.fixture(autouse=True)
def enforce_ssrf_checks(monkeypatch):
    """Production posture: local/private targets are not exempt."""
    monkeypatch.setattr(settings, "allow_local_test", False)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/api",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://10.0.0.5/internal",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://[::1]/",
        "http://0.0.0.0/",
        "file:///etc/passwd",
        "gopher://example.com/",
        "http://user:pass@example.com/",
        "https://[fd00::1]/",
    ],
)
def test_validate_outbound_url_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        validate_outbound_url(url, resolve_dns=False)


@pytest.mark.parametrize("url", ["https://example.com/orders", "http://api.example.com:8443/v1"])
def test_validate_outbound_url_allows_public_targets(url):
    validate_outbound_url(url, resolve_dns=False)


def test_allow_local_test_bypasses_checks(monkeypatch):
    monkeypatch.setattr(settings, "allow_local_test", True)
    validate_outbound_url("http://127.0.0.1:8000/api", resolve_dns=False)


def test_dns_resolved_private_address_is_blocked(monkeypatch):
    """A public hostname resolving to a private address must still be blocked."""
    monkeypatch.setattr(
        "app.core.url_safety.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("169.254.169.254", 80))],
    )
    with pytest.raises(ValueError):
        validate_outbound_url("http://rebind.example.com/")


@pytest.mark.asyncio
async def test_execute_resource_request_blocks_internal_target():
    result = await execute_resource_request(
        connection_mode="direct",
        url="http://169.254.169.254/latest/meta-data/",
        http_method="GET",
        connection=None,
        fixed_headers=[],
        payload={},
        user_email="ops@getnexar.com",
    )
    assert result["success"] is False
    assert result["status_code"] is None
    assert "Blocked request" in result["error"]


@pytest.mark.asyncio
async def test_execute_resource_request_blocks_url_param_injection():
    """A URL placeholder must not be able to redirect the request off-host."""
    result = await execute_resource_request(
        connection_mode="direct",
        url="http://{host}/data",
        http_method="GET",
        connection=None,
        fixed_headers=[],
        payload={"host": "127.0.0.1"},
        user_email="ops@getnexar.com",
    )
    assert result["success"] is False
    assert "Blocked request" in result["error"]


@pytest.mark.asyncio
async def test_internal_tool_cannot_leave_internal_base():
    result = await execute_resource_request(
        connection_mode="direct",
        url="/api/sim/devices",
        http_method="GET",
        connection=None,
        fixed_headers=[],
        payload={},
        user_email="ops@getnexar.com",
        tool_scope="internal",
    )
    # Reaches the network layer (connection error), i.e. it was not blocked by validation.
    assert "Blocked request" not in (result["error"] or "")


def test_secret_header_requires_allowed_prefix(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@db/nexar")
    monkeypatch.setenv(f"{settings.resource_secret_env_prefix}PARTNER_KEY", "sk-partner")

    headers = merge_headers(
        None,
        [
            {"key": "X-Leak", "value": "DATABASE_URL", "is_secret": True},
            {
                "key": "X-Partner",
                "value": f"{settings.resource_secret_env_prefix}PARTNER_KEY",
                "is_secret": True,
            },
        ],
        "ops@getnexar.com",
    )

    assert "X-Leak" not in headers
    assert headers["X-Partner"] == "sk-partner"
    assert headers["X-Nexar-User"] == "ops@getnexar.com"


def test_secret_header_omitted_when_env_missing():
    headers = merge_headers(
        None,
        [
            {
                "key": "X-Missing",
                "value": f"{settings.resource_secret_env_prefix}NOT_SET",
                "is_secret": True,
            }
        ],
        "ops@getnexar.com",
    )
    assert "X-Missing" not in headers


def test_resource_create_rejects_private_url():
    with pytest.raises(ValueError):
        ResourceCreate(
            name="metadata_probe",
            connection_mode="direct",
            http_method="GET",
            url="http://169.254.169.254/latest/meta-data/",
        )


def test_connection_create_rejects_private_base_url():
    with pytest.raises(ValueError):
        ConnectionCreate(name="internal", base_url="http://127.0.0.1:5432")
