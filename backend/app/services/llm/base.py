import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar

_T = TypeVar("_T")

# Substrings that mark a transient LLM failure worth retrying (rate limit / overloaded / 5xx).
_RETRYABLE_MARKERS = (
    "429",
    "rate limit",
    "rate_limit",
    "resource_exhausted",
    "resourceexhausted",
    "503",
    "unavailable",
    "overloaded",
    "try again",
)


def _is_retryable_llm_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _RETRYABLE_MARKERS)


async def with_llm_retry(
    call: Callable[[], Awaitable[_T]],
    *,
    attempts: int,
    base_delay: float,
    timeout: float,
) -> _T:
    """Run an LLM API call with a per-attempt timeout and bounded exponential backoff.

    Retries only transient failures (rate limit / overloaded / 5xx / timeout); anything
    else raises immediately. ponytail: tiny inline retry, no `tenacity` dependency.
    """
    for attempt in range(attempts):
        try:
            return await asyncio.wait_for(call(), timeout)
        except Exception as exc:  # noqa: BLE001
            retryable = isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or _is_retryable_llm_error(exc)
            if attempt == attempts - 1 or not retryable:
                raise
            await asyncio.sleep(base_delay * (2**attempt))
    raise RuntimeError("unreachable")  # loop either returns or raises


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


ChatRole = Literal["system", "user", "assistant", "tool"]


@dataclass
class ChatMessage:
    role: ChatRole
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
    name: str | None = None

    def to_provider_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            payload["content"] = self.content
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            payload["name"] = self.name
        if self.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": _stringify_arguments(call.arguments),
                    },
                }
                for call in self.tool_calls
            ]
        return payload


def _stringify_arguments(arguments: dict[str, Any]) -> str:
    import json

    return json.dumps(arguments)


class LLMProvider:
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] = "auto",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        raise NotImplementedError
