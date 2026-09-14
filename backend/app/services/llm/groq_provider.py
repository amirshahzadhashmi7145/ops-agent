import json
from typing import Any, Literal

from groq import AsyncGroq

from app.core.config import settings
from app.services.llm.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ToolCall,
    with_llm_retry,
)

TOOL_CALL_RETRY_HINT = (
    "If you call a tool, emit a valid function call only. "
    "Use one tool at a time, and provide strictly valid JSON arguments."
)


def _is_tool_use_failed_error(exc: Exception) -> bool:
    message = str(exc)
    return "tool_use_failed" in message or "Failed to call a function" in message


class GroqProvider(LLMProvider):
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] = "auto",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        token_limit = max_tokens if max_tokens is not None else settings.llm_max_tokens
        temp = temperature if temperature is not None else settings.llm_temperature
        request: dict[str, Any] = {
            "model": self._model,
            "messages": [message.to_provider_dict() for message in messages],
            "temperature": temp,
            "max_tokens": token_limit,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = tool_choice

        try:
            response = await with_llm_retry(
                lambda: self._client.chat.completions.create(**request),
                attempts=settings.llm_max_attempts,
                base_delay=settings.llm_retry_base_delay,
                timeout=settings.llm_timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            if tools and tool_choice != "none" and _is_tool_use_failed_error(exc):
                retry_request = dict(request)
                retry_request["messages"] = [
                    *request["messages"],
                    {"role": "system", "content": TOOL_CALL_RETRY_HINT},
                ]
                try:
                    response = await self._client.chat.completions.create(**retry_request)
                except Exception as retry_exc:  # noqa: BLE001
                    # Last-resort fallback: return a normal response without tool calls.
                    if _is_tool_use_failed_error(retry_exc):
                        fallback_request: dict[str, Any] = {
                            "model": self._model,
                            "messages": request["messages"],
                            "temperature": temp,
                            "max_tokens": token_limit,
                        }
                        response = await self._client.chat.completions.create(**fallback_request)
                    else:
                        raise
            else:
                raise
        choice = response.choices[0].message
        tool_calls: list[ToolCall] = []
        if choice.tool_calls:
            for call in choice.tool_calls:
                raw_args = call.function.arguments or "{}"
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    arguments = {}
                tool_calls.append(
                    ToolCall(
                        id=call.id,
                        name=call.function.name,
                        arguments=arguments if isinstance(arguments, dict) else {},
                    )
                )

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        return LLMResponse(
            content=choice.content,
            tool_calls=tool_calls,
            model=self._model,
            usage=usage,
        )
