"""Researcher sub-agent for information gathering tasks."""

from typing import Any, Callable

from honolulu.agents.base import SubAgent, SubAgentResult
from honolulu.models.base import ModelProvider
from honolulu.tools.base import Tool


class ResearcherAgent(SubAgent):
    """Sub-agent specialized in research and information gathering."""

    name = "researcher"
    display_name = "Researcher Agent"
    description = "Specialized in searching the web, gathering information, and summarizing findings"

    def __init__(
        self,
        model: ModelProvider,
        tools: list[Tool] | None = None,
        system_prompt: str | None = None,
    ):
        super().__init__(model, tools, system_prompt)

    def _default_system_prompt(self) -> str:
        return """You are a skilled research agent. Your job is to find and synthesize information.

Capabilities:
- Search the web for information
- Fetch and read web pages
- Summarize and analyze findings
- Provide well-organized research results

Guidelines:
1. Use multiple sources when possible
2. Verify information across sources
3. Cite your sources
4. Organize findings clearly
5. Distinguish facts from opinions

When given a research task:
1. Understand what information is needed
2. Search for relevant sources
3. Read and analyze the content
4. Synthesize the findings
5. Present a clear summary with sources

Be thorough but concise. Focus on the most relevant and reliable information."""

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> SubAgentResult:
        """Execute a research task."""
        return await self._run_agent_loop(
            task=task,
            context=context,
            on_progress=on_progress,
            max_iterations=10,
        )
