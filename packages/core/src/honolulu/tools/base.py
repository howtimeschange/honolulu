"""Base classes for the tool system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: Any
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


class Tool(ABC):
    """Abstract base class for all tools."""

    name: str
    description: str
    parameters: dict  # JSON Schema format
    requires_confirmation: bool = False

    @abstractmethod
    async def execute(self, **params: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def to_anthropic_tool(self) -> dict:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


@dataclass
class ToolManager:
    """Manages tool registration and execution."""

    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool

    def register_all(self, tools: list[Tool]) -> None:
        """Register multiple tools."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())

    def get_tool_definitions(self) -> list[dict]:
        """Get all tool definitions in Anthropic format."""
        return [tool.to_anthropic_tool() for tool in self.tools.values()]

    async def execute(self, name: str, params: dict) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{name}' not found",
            )

        try:
            return await tool.execute(**params)
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )

    def requires_confirmation(self, name: str) -> bool:
        """Check if a tool requires user confirmation."""
        tool = self.get(name)
        return tool.requires_confirmation if tool else False
