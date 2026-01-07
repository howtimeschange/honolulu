"""OpenAI-compatible model provider."""

import json
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from honolulu.models.base import ModelProvider, ModelResponse, StreamChunk, ToolCall


class OpenAIProvider(ModelProvider):
    """OpenAI and OpenAI-compatible model provider."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ):
        self.client = AsyncOpenAI(
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
        """Make a non-streaming call to the model."""
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages, system)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = await self.client.chat.completions.create(**kwargs)

        # Parse response
        content = None
        tool_calls = []
        choice = response.choices[0]

        if choice.message.content:
            content = choice.message.content

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

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
        """Make a streaming call to the model."""
        openai_messages = self._convert_messages(messages, system)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        current_tool_calls: dict[int, dict] = {}

        stream = await self.client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Handle text content
            if delta.content:
                yield StreamChunk(type="text", content=delta.content)

            # Handle tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index

                    if idx not in current_tool_calls:
                        # New tool call
                        current_tool_calls[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name if tc.function else "",
                            "arguments": "",
                        }
                        if tc.id:
                            yield StreamChunk(
                                type="tool_use_start",
                                tool_call=ToolCall(
                                    id=tc.id,
                                    name=tc.function.name if tc.function else "",
                                    arguments={},
                                ),
                            )

                    # Accumulate arguments
                    if tc.function and tc.function.arguments:
                        current_tool_calls[idx]["arguments"] += tc.function.arguments
                        yield StreamChunk(
                            type="tool_use_delta",
                            content=tc.function.arguments,
                        )

            # Check for finish
            if chunk.choices[0].finish_reason:
                # Emit completed tool calls
                for idx, tc_data in current_tool_calls.items():
                    try:
                        arguments = json.loads(tc_data["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}

                    yield StreamChunk(
                        type="tool_use_end",
                        tool_call=ToolCall(
                            id=tc_data["id"],
                            name=tc_data["name"],
                            arguments=arguments,
                        ),
                    )

    def _convert_messages(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> list[dict]:
        """Convert Anthropic-style messages to OpenAI format."""
        openai_messages = []

        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            if role == "user":
                if isinstance(content, list):
                    # Handle tool results
                    for item in content:
                        if item.get("type") == "tool_result":
                            openai_messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": item["tool_use_id"],
                                    "content": item["content"],
                                }
                            )
                        else:
                            openai_messages.append({"role": "user", "content": str(content)})
                            break
                else:
                    openai_messages.append({"role": "user", "content": content})

            elif role == "assistant":
                assistant_msg: dict[str, Any] = {"role": "assistant"}

                if isinstance(content, list):
                    text_parts = []
                    tool_calls = []

                    for item in content:
                        if item.get("type") == "text":
                            text_parts.append(item["text"])
                        elif item.get("type") == "tool_use":
                            tool_calls.append(
                                {
                                    "id": item["id"],
                                    "type": "function",
                                    "function": {
                                        "name": item["name"],
                                        "arguments": json.dumps(item["input"]),
                                    },
                                }
                            )

                    if text_parts:
                        assistant_msg["content"] = "\n".join(text_parts)
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                else:
                    assistant_msg["content"] = content

                openai_messages.append(assistant_msg)

        return openai_messages

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert Anthropic tool format to OpenAI format."""
        openai_tools = []

        for tool in tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                }
            )

        return openai_tools
