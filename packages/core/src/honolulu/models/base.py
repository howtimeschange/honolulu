"""Base classes for model providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator


@dataclass
class ToolCall:
    """Represents a tool call from the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelResponse:
    """Response from a model."""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """A chunk of streaming response."""

    type: str  # "text", "tool_use_start", "tool_use_delta", "tool_use_end"
    content: str | None = None
    tool_call: ToolCall | None = None


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    name: str

    @abstractmethod
    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> ModelResponse:
        """Make a non-streaming call to the model."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Make a streaming call to the model."""
        pass
