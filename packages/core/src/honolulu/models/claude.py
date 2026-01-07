"""Claude model provider using Anthropic SDK."""

import json
from typing import Any, AsyncGenerator

from anthropic import AsyncAnthropic

from honolulu.models.base import ModelProvider, ModelResponse, StreamChunk, ToolCall


class ClaudeProvider(ModelProvider):
    """Claude model provider using Anthropic API."""

    name = "claude"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        base_url: str | None = None,
    ):
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> ModelResponse:
        """Make a non-streaming call to Claude."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        # Parse response
        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Make a streaming call to Claude."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        current_tool_call: dict[str, Any] | None = None

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "text":
                        pass  # Text will come in deltas
                    elif block.type == "tool_use":
                        current_tool_call = {
                            "id": block.id,
                            "name": block.name,
                            "arguments_json": "",
                        }
                        yield StreamChunk(
                            type="tool_use_start",
                            tool_call=ToolCall(
                                id=block.id,
                                name=block.name,
                                arguments={},
                            ),
                        )

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield StreamChunk(type="text", content=delta.text)
                    elif delta.type == "input_json_delta":
                        if current_tool_call:
                            current_tool_call["arguments_json"] += delta.partial_json
                            yield StreamChunk(
                                type="tool_use_delta",
                                content=delta.partial_json,
                            )

                elif event.type == "content_block_stop":
                    if current_tool_call:
                        # Parse the complete arguments
                        try:
                            arguments = json.loads(
                                current_tool_call["arguments_json"]
                            )
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
