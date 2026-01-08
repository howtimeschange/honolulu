"""Orchestrator agent that coordinates sub-agents."""

from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable

from honolulu.agent import Agent, AgentEvent
from honolulu.models.base import ModelProvider
from honolulu.tools.base import Tool, ToolResult, ToolManager
from honolulu.agents.base import SubAgent, SubAgentResult


@dataclass
class DelegationTool(Tool):
    """A tool that delegates to a sub-agent."""

    name: str
    description: str
    parameters: dict
    requires_confirmation: bool = False

    _sub_agent: SubAgent | None = None
    _on_sub_agent_event: Callable[[str, str, str], None] | None = None

    def __init__(
        self,
        sub_agent: SubAgent,
        on_sub_agent_event: Callable[[str, str, str], None] | None = None,
    ):
        self.name = f"delegate_to_{sub_agent.name}"
        self.description = f"Delegate a task to the {sub_agent.display_name}. {sub_agent.description}"
        self.parameters = {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task to delegate to the sub-agent",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context for the task (optional)",
                },
            },
            "required": ["task"],
        }
        self._sub_agent = sub_agent
        self._on_sub_agent_event = on_sub_agent_event

    async def execute(self, task: str, context: str | None = None, **kwargs: Any) -> ToolResult:
        """Execute the delegation."""
        if not self._sub_agent:
            return ToolResult(success=False, output=None, error="Sub-agent not configured")

        # Notify start
        if self._on_sub_agent_event:
            self._on_sub_agent_event(self._sub_agent.name, "start", task)

        def on_progress(content: str) -> None:
            if self._on_sub_agent_event:
                self._on_sub_agent_event(self._sub_agent.name, "progress", content)

        try:
            ctx = {"context": context} if context else None
            result = await self._sub_agent.execute(task, context=ctx, on_progress=on_progress)

            # Notify done
            if self._on_sub_agent_event:
                self._on_sub_agent_event(self._sub_agent.name, "done", result.output)

            if result.success:
                return ToolResult(success=True, output=result.output)
            else:
                return ToolResult(success=False, output=None, error=result.error)
        except Exception as e:
            if self._on_sub_agent_event:
                self._on_sub_agent_event(self._sub_agent.name, "error", str(e))
            return ToolResult(success=False, output=None, error=str(e))


class Orchestrator:
    """Main orchestrator that coordinates sub-agents."""

    SYSTEM_PROMPT = """You are an AI orchestrator that coordinates specialized sub-agents to complete tasks.

You have access to the following sub-agents through delegation tools:
- Coder Agent: Specialized in writing, reading, and debugging code
- Researcher Agent: Specialized in searching the web and gathering information

When a user asks you to do something:
1. Analyze the task to understand what needs to be done
2. Break down complex tasks into smaller steps if needed
3. Delegate specific parts to the appropriate sub-agent
4. Coordinate the results and provide a unified response

Guidelines:
- Use delegate_to_coder for coding tasks (writing code, debugging, file operations)
- Use delegate_to_researcher for information gathering (web search, research)
- You can combine multiple sub-agents for complex tasks
- Always explain your plan before delegating
- Summarize the results after sub-agents complete their work
"""

    def __init__(
        self,
        model: ModelProvider,
        sub_agents: list[SubAgent],
        tool_manager: ToolManager,
        on_sub_agent_event: Callable[[str, str, str], None] | None = None,
    ):
        self.model = model
        self.sub_agents = {sa.name: sa for sa in sub_agents}
        self.tool_manager = tool_manager
        self._on_sub_agent_event = on_sub_agent_event

        # Register delegation tools
        for sub_agent in sub_agents:
            delegation_tool = DelegationTool(
                sub_agent=sub_agent,
                on_sub_agent_event=on_sub_agent_event,
            )
            self.tool_manager.register(delegation_tool)

    def get_tool_definitions(self) -> list[dict]:
        """Get all available tools including delegation tools."""
        return self.tool_manager.get_tool_definitions()


def create_orchestrator(
    model: ModelProvider,
    tool_manager: ToolManager,
    on_sub_agent_event: Callable[[str, str, str], None] | None = None,
) -> Orchestrator:
    """Create an orchestrator with default sub-agents."""
    from honolulu.agents.sub_agents import CoderAgent, ResearcherAgent
    from honolulu.tools import get_file_tools, get_bash_tools, get_web_tools

    # Create sub-agents with their specialized tools
    coder = CoderAgent(
        model=model,
        tools=get_file_tools() + get_bash_tools(),
    )

    researcher = ResearcherAgent(
        model=model,
        tools=get_web_tools(),
    )

    return Orchestrator(
        model=model,
        sub_agents=[coder, researcher],
        tool_manager=tool_manager,
        on_sub_agent_event=on_sub_agent_event,
    )
