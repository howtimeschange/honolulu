"""OpenAI-compatible model provider."""

import json
from typing import Any, AsyncGenerator

from honolulu.models.base import ModelProvider, ModelResponse, StreamChunk, ToolCall


class OpenAIProvider(ModelProvider):
    """OpenAI-compatible model provider (works with OpenAI, Qwen, etc.)."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install honolulu[routing]"
            )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    def _convert_tools(self, tools: list[dict] | None) -> list[dict] | None:
        """Convert Anthropic tool format to OpenAI format."""
        if not tools:
            return None

        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                },
            })
        return openai_tools

    def _convert_messages(self, messages: list[dict], system: str | None) -> list[dict]:
        """Convert Anthropic message format to OpenAI format."""
        openai_messages = []

        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                openai_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle tool results
                for block in content:
                    if block.get("type") == "tool_result":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": str(block.get("content", "")),
                        })
                    elif block.get("type") == "text":
                        openai_messages.append({"role": role, "content": block["text"]})

        return openai_messages

    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> ModelResponse:
        """Make a non-streaming call."""
        openai_messages = self._convert_messages(messages, system)
        openai_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        response = await self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
                ))

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Make a streaming call."""
        openai_messages = self._convert_messages(messages, system)
        openai_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        current_tool_call: dict[str, Any] | None = None

        stream = await self.client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if not delta:
                continue

            if delta.content:
                yield StreamChunk(type="text", content=delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.function and tc.function.name:
                        # New tool call starting
                        current_tool_call = {
                            "id": tc.id or "",
                            "name": tc.function.name,
                            "arguments_json": tc.function.arguments or "",
                        }
                        yield StreamChunk(
                            type="tool_use_start",
                            tool_call=ToolCall(
                                id=tc.id or "",
                                name=tc.function.name,
                                arguments={},
                            ),
                        )
                    elif tc.function and tc.function.arguments and current_tool_call:
                        current_tool_call["arguments_json"] += tc.function.arguments
                        yield StreamChunk(
                            type="tool_use_delta",
                            content=tc.function.arguments,
                        )

            if chunk.choices[0].finish_reason and current_tool_call:
                try:
                    arguments = json.loads(current_tool_call["arguments_json"])
                except json.JSONDecodeError:
                    arguments = {}

                yield StreamChunk(
                    type="tool_use_end",
                    tool_call=ToolCall(
                        id=current_tool_call["id"],
                        name=current_tool_call["name"],
                        arguments=arguments,
                    ),
                )
                current_tool_call = None
