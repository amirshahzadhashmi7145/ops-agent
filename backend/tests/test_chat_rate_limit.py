"""In-process chat/API rate limiter (app.core.rate_limit)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core import rate_limit
from app.core.rate_limit import _client_key, enforce_rate_limit


def _request(*, host: str = "203.0.113.10", forwarded: str | None = None):
    headers = {}
    if forwarded is not None:
        headers["x-forwarded-for"] = forwarded
    return SimpleNamespace(
        headers=headers,
        client=SimpleNamespace(host=host) if host else None,
    )


@pytest.fixture(autouse=True)
def _clear_hits():
    rate_limit._hits.clear()
    yield
    rate_limit._hits.clear()


def test_client_key_prefers_forwarded_for():
    req = _request(forwarded="198.51.100.1, 203.0.113.5")
    assert _client_key(req) == "198.51.100.1"  # type: ignore[arg-type]


def test_client_key_falls_back_to_peer_host():
    assert _client_key(_request(host="203.0.113.9")) == "203.0.113.9"  # type: ignore[arg-type]
    assert _client_key(_request(host="")) == "unknown"  # type: ignore[arg-type]


def test_enforce_rate_limit_disabled_when_limit_zero(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_per_minute", 0)
    req = _request()
    for _ in range(5):
        enforce_rate_limit(req)  # type: ignore[arg-type]
    assert rate_limit._hits == {}


def test_enforce_rate_limit_blocks_after_window(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_per_minute", 3)
    req = _request()
    enforce_rate_limit(req)  # type: ignore[arg-type]
    enforce_rate_limit(req)  # type: ignore[arg-type]
    enforce_rate_limit(req)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        enforce_rate_limit(req)  # type: ignore[arg-type]
    assert exc.value.status_code == 429


def test_enforce_rate_limit_expires_old_hits(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_per_minute", 2)
    req = _request()
    # Seed two hits just outside the 60s window, then a fresh call should pass.
    with patch("app.core.rate_limit.time.monotonic", side_effect=[100.0, 100.0, 161.0]):
        enforce_rate_limit(req)  # type: ignore[arg-type]
        enforce_rate_limit(req)  # type: ignore[arg-type]
        enforce_rate_limit(req)  # type: ignore[arg-type]  # old hits pruned
