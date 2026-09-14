from typing import Any, Literal

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.llm.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ToolCall,
    with_llm_retry,
)


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        self._client = genai.Client(api_key=settings.google_api_key)
        self._model = settings.gemini_model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] = "auto",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        system_instruction = None
        contents: list[types.Content] = []
        for message in messages:
            if message.role == "system":
                system_instruction = message.content
                continue
            if message.role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=message.name or "tool",
                                response={"result": message.content or ""},
                            )
                        ],
                    )
                )
                continue
            if message.role == "assistant" and message.tool_calls:
                parts: list[types.Part] = []
                if message.content:
                    parts.append(types.Part.from_text(text=message.content))
                for call in message.tool_calls:
                    parts.append(
                        types.Part.from_function_call(
                            name=call.name,
                            args=call.arguments,
                        )
                    )
                contents.append(types.Content(role="model", parts=parts))
                continue

            role = "model" if message.role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=message.content or "")],
                )
            )

        config_kwargs: dict[str, Any] = {
            "temperature": temperature if temperature is not None else settings.llm_temperature,
            "max_output_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools and tool_choice != "none":
            declarations = []
            for tool in tools:
                fn = tool.get("function", {})
                declarations.append(
                    types.FunctionDeclaration(
                        name=fn.get("name", ""),
                        description=fn.get("description", ""),
                        parameters=fn.get("parameters"),
                    )
                )
            config_kwargs["tools"] = [types.Tool(function_declarations=declarations)]
            if tool_choice == "required":
                config_kwargs["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                )

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
        response = await with_llm_retry(
            lambda: self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            ),
            attempts=settings.llm_max_attempts,
            base_delay=settings.llm_retry_base_delay,
            timeout=settings.llm_timeout_seconds,
        )

        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []
        # A blocked/empty candidate (finish_reason SAFETY/RECITATION) has content=None; guard
        # against it so we return an empty response instead of raising AttributeError.
        candidate = response.candidates[0] if response.candidates else None
        content = getattr(candidate, "content", None) if candidate else None
        if content is not None:
            for part in content.parts or []:
                if getattr(part, "text", None):
                    text_parts.append(part.text)
                function_call = getattr(part, "function_call", None)
                if function_call and function_call.name:
                    args = function_call.args or {}
                    if not isinstance(args, dict):
                        args = dict(args)
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{function_call.name}",
                            name=function_call.name,
                            arguments=args,
                        )
                    )

        usage: dict[str, int] = {}
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }

        return LLMResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            model=self._model,
            usage=usage,
        )
