import pytest

from app.schemas.resource import ResourceCreate
from app.services.resource_executor import build_resolved_url, resolve_test_headers


class FakeConnection:
    base_url = "https://api.example.com"


def test_build_resolved_url_direct_with_params():
    url = build_resolved_url("direct", "https://httpbin.org/get/{id}", None, {"id": "42"})
    assert url == "https://httpbin.org/get/42"


def test_build_resolved_url_existing_connection():
    url = build_resolved_url("existing", "/orders/{id}", FakeConnection(), {"id": "99"})
    assert url == "https://api.example.com/orders/99"


def test_resource_create_name_validation():
    resource = ResourceCreate(
        name="get-order",
        description="test",
        connection_mode="direct",
        http_method="GET",
        url="https://example.com",
    )
    assert resource.name == "get-order"


def test_resource_create_invalid_name():
    with pytest.raises(ValueError):
        ResourceCreate(
            name="bad name!",
            description="test",
            connection_mode="direct",
            http_method="GET",
            url="https://example.com",
        )


def test_resolve_test_headers_inherits_fixed_when_test_empty():
    fixed = [{"key": "Authorization", "value": "Bearer token"}]
    assert resolve_test_headers(fixed, []) == fixed
    assert resolve_test_headers(fixed, None) == fixed


def test_resolve_test_headers_uses_test_overrides():
    fixed = [{"key": "Authorization", "value": "Bearer old"}]
    test = [{"key": "Authorization", "value": "Bearer new"}]
    result = resolve_test_headers(fixed, test)
    assert len(result) == 1
    assert result[0]["value"] == "Bearer new"


def test_resolve_test_headers_keeps_fixed_when_test_value_empty():
    fixed = [{"key": "Authorization", "value": "Bearer saved"}]
    test = [{"key": "Authorization", "value": ""}]
    result = resolve_test_headers(fixed, test)
    assert result == fixed


def test_resolve_test_headers_merges_partial_overrides():
    fixed = [
        {"key": "Authorization", "value": "Bearer saved"},
        {"key": "X-Custom", "value": "fixed"},
    ]
    test = [{"key": "Authorization", "value": "Bearer override"}]
    result = {item["key"]: item["value"] for item in resolve_test_headers(fixed, test)}
    assert result["Authorization"] == "Bearer override"
    assert result["X-Custom"] == "fixed"
