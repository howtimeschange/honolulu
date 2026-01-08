"""Coder sub-agent for code-related tasks."""

from typing import Any, Callable

from honolulu.agents.base import SubAgent, SubAgentResult
from honolulu.models.base import ModelProvider
from honolulu.tools.base import Tool


class CoderAgent(SubAgent):
    """Sub-agent specialized in coding tasks."""

    name = "coder"
    display_name = "Coder Agent"
    description = "Specialized in writing, reading, debugging code, and executing shell commands"

    def __init__(
        self,
        model: ModelProvider,
        tools: list[Tool] | None = None,
        system_prompt: str | None = None,
    ):
        super().__init__(model, tools, system_prompt)

    def _default_system_prompt(self) -> str:
        return """You are a skilled software developer agent. Your job is to help with coding tasks.

Capabilities:
- Read and write files
- Execute shell commands
- Write clean, well-documented code
- Debug and fix issues

Guidelines:
1. Always read existing files before modifying them
2. Write clear, concise code with appropriate comments
3. Follow the project's existing code style
4. Test your changes when possible
5. Handle errors gracefully

When given a task:
1. First understand what needs to be done
2. Read relevant files to understand the context
3. Plan your approach
4. Implement the solution step by step
5. Verify the result

Be efficient and focused. Complete the task and report the results clearly."""

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> SubAgentResult:
        """Execute a coding task."""
        return await self._run_agent_loop(
            task=task,
            context=context,
            on_progress=on_progress,
            max_iterations=15,  # Allow more iterations for complex coding tasks
        )
