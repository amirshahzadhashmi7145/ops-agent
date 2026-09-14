from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.services.llm.base import ChatMessage
from app.services.llm.factory import get_llm_provider
from app.services.llm.openai_provider import OpenAIProvider


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    get_llm_provider.cache_clear()
    yield
    get_llm_provider.cache_clear()


def test_factory_selects_openai(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_base_url", "")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "vertex")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_llm_provider()


def test_openai_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIProvider()


@pytest.mark.asyncio
async def test_openai_parses_tool_calls(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "openai_base_url", "")
    monkeypatch.setattr(settings, "llm_temperature", 0.2)
    monkeypatch.setattr(settings, "llm_max_tokens", 256)
    monkeypatch.setattr(settings, "llm_max_attempts", 1)
    monkeypatch.setattr(settings, "llm_retry_base_delay", 0.0)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 5.0)

    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="search_kb", arguments='{"query":"reboot"}'),
    )
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, tool_calls=[tool_call]),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=4, total_tokens=14),
    )
    create = AsyncMock(return_value=response)

    provider = OpenAIProvider()
    with patch.object(provider._client.chat.completions, "create", create):
        result = await provider.chat(
            [ChatMessage(role="user", content="how do I reboot?")],
            tools=[{"type": "function", "function": {"name": "search_kb"}}],
        )

    assert result.model == "gpt-4o-mini"
    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_kb"
    assert result.tool_calls[0].arguments == {"query": "reboot"}
    create.assert_awaited_once()
