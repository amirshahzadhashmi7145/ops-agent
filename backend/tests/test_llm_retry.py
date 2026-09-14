import asyncio

import pytest

from app.services.llm.base import _is_retryable_llm_error, with_llm_retry


def test_is_retryable_classification():
    assert _is_retryable_llm_error(Exception("Error code: 429 rate limit"))
    assert _is_retryable_llm_error(Exception("503 Service Unavailable"))
    assert _is_retryable_llm_error(Exception("RESOURCE_EXHAUSTED"))
    assert _is_retryable_llm_error(Exception("model is overloaded"))
    assert not _is_retryable_llm_error(Exception("invalid api key"))
    assert not _is_retryable_llm_error(ValueError("bad request"))


@pytest.mark.asyncio
async def test_retries_transient_then_succeeds():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise Exception("429 rate limit reached")
        return "ok"

    result = await with_llm_retry(flaky, attempts=3, base_delay=0.0, timeout=5)
    assert result == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_non_retryable_raises_immediately():
    calls = {"n": 0}

    async def bad():
        calls["n"] += 1
        raise ValueError("bad request")

    with pytest.raises(ValueError):
        await with_llm_retry(bad, attempts=3, base_delay=0.0, timeout=5)
    assert calls["n"] == 1  # no retries for non-retryable errors


@pytest.mark.asyncio
async def test_exhausts_attempts_then_raises():
    calls = {"n": 0}

    async def always_429():
        calls["n"] += 1
        raise Exception("503 unavailable")

    with pytest.raises(Exception):
        await with_llm_retry(always_429, attempts=2, base_delay=0.0, timeout=5)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_timeout_is_retried():
    calls = {"n": 0}

    async def slow_then_fast():
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.sleep(1)  # exceeds the 0.05s timeout on the first attempt
        return "ok"

    result = await with_llm_retry(slow_then_fast, attempts=2, base_delay=0.0, timeout=0.05)
    assert result == "ok"
    assert calls["n"] == 2
