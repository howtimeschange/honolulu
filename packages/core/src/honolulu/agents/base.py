"""Base classes for sub-agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable

from honolulu.models.base import ModelProvider
from honolulu.tools.base import Tool, ToolResult, ToolManager


@dataclass
class SubAgentResult:
    """Result from a sub-agent execution."""

    success: bool
    output: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class SubAgent(ABC):
    """Base class for specialized sub-agents."""

    name: str = "base"
    display_name: str = "Base Agent"
    description: str = "A base sub-agent"

    def __init__(
        self,
        model: ModelProvider,
        tools: list[Tool] | None = None,
        system_prompt: str | None = None,
    ):
        self.model = model
        self.tool_manager = ToolManager()
        if tools:
            self.tool_manager.register_all(tools)
        self._system_prompt = system_prompt or self._default_system_prompt()

    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Get the default system prompt for this agent."""
        pass

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> SubAgentResult:
        """Execute a task and return the result."""
        pass

    async def _run_agent_loop(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        on_progress: Callable[[str], None] | None = None,
        max_iterations: int = 10,
    ) -> SubAgentResult:
        """Run the agent loop with tool execution."""
        messages = []

        # Add context if provided
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            messages.append({
                "role": "user",
                "content": f"Context:\n{context_str}\n\nTask: {task}",
            })
        else:
            messages.append({"role": "user", "content": task})

        tools = self.tool_manager.get_tool_definitions()
        artifacts: dict[str, Any] = {}

        for _ in range(max_iterations):
            # Call the model
            response = await self.model.call(
                messages=messages,
                tools=tools if tools else None,
                system=self._system_prompt,
            )

            # If there's text content, report progress
            if response.content and on_progress:
                on_progress(response.content)

            # If no tool calls, we're done
            if not response.has_tool_calls:
                return SubAgentResult(
                    success=True,
                    output=response.content or "",
                    artifacts=artifacts,
                )

            # Process tool calls
            tool_results = []
            for tool_call in response.tool_calls:
                tool = self.tool_manager.get_tool(tool_call.name)
                if tool:
                    result = await tool.execute(**tool_call.arguments)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": str(result.output) if result.success else f"Error: {result.error}",
                    })

                    # Store artifacts (e.g., files written)
                    if tool_call.name in ["write_file", "read_file"]:
                        path = tool_call.arguments.get("path", "")
                        if path:
                            artifacts[path] = result.output
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": f"Error: Tool '{tool_call.name}' not found",
                    })

            # Add assistant message with tool use
            messages.append({
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                    for tc in response.tool_calls
                ],
            })

            # Add tool results
            messages.append({
                "role": "user",
                "content": tool_results,
            })

        # Max iterations reached
        return SubAgentResult(
            success=False,
            output="",
            error="Max iterations reached",
            artifacts=artifacts,
        )
