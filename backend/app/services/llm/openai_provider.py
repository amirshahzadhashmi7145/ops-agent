import json
from typing import Any, Literal

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.llm.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ToolCall,
    with_llm_retry,
)


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = settings.openai_model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] = "auto",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        request: dict[str, Any] = {
            "model": self._model,
            "messages": [message.to_provider_dict() for message in messages],
            "temperature": temperature if temperature is not None else settings.llm_temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = tool_choice

        response = await with_llm_retry(
            lambda: self._client.chat.completions.create(**request),
            attempts=settings.llm_max_attempts,
            base_delay=settings.llm_retry_base_delay,
            timeout=settings.llm_timeout_seconds,
        )
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
