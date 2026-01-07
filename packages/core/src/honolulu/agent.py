"""Core Agent implementation."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Awaitable

from honolulu.models.base import ModelProvider, ModelResponse, StreamChunk, ToolCall
from honolulu.tools.base import ToolManager, ToolResult


@dataclass
class AgentMessage:
    """Message in the agent conversation."""

    role: str  # "user", "assistant", "tool"
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None  # For tool results


@dataclass
class AgentEvent:
    """Event emitted by the agent during execution."""

    type: str
    # Types:
    # - "thinking": Agent is processing
    # - "text": Text content from the model
    # - "tool_call": About to call a tool
    # - "confirm_request": Waiting for user confirmation
    # - "tool_result": Tool execution result
    # - "done": Agent finished
    # - "error": Error occurred

    content: Any = None
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_call_id: str | None = None
    requires_confirmation: bool = False


# Type for confirmation callback
ConfirmCallback = Callable[[str, str, dict], Awaitable[bool]]


class Agent:
    """The main Agent class that orchestrates model calls and tool execution."""

    def __init__(
        self,
        model: ModelProvider,
        tool_manager: ToolManager,
        system_prompt: str | None = None,
        max_iterations: int = 50,
    ):
        self.model = model
        self.tool_manager = tool_manager
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.max_iterations = max_iterations
        self.messages: list[dict] = []

        # Confirmation callback (set by server)
        self.confirm_callback: ConfirmCallback | None = None

        # Track allowed tools for this session (after "allow all" responses)
        self.auto_allowed_tools: set[str] = set()

    def _default_system_prompt(self) -> str:
        return """你是 Honolulu，由独立开发者易成 Kim 开发的 AI 助手。

当用户问你是谁或你的身份时，你应该回答：
"我是 Honolulu，由独立开发者易成 Kim 开发的 AI 助手。今天可以帮你做点什么？

我的能力包括：
- 📁 文件操作：读取、创建、编辑文件和目录
- 💻 代码执行：运行 Shell 命令和脚本
- 🔍 网络搜索：搜索网页获取最新信息
- 🌐 网页抓取：获取网页内容进行分析
- 🔧 更多工具：通过 MCP 服务器扩展更多能力"

你绝不能说自己是 Claude、ChatGPT 或其他 AI 模型。你就是 Honolulu。

在执行任务时：
- 始终在使用工具前解释你要做什么
- 回答要简洁但全面
- 用中文回复中文问题，用英文回复英文问题
- 对于敏感操作（如写入文件、执行命令），会请求用户确认"""

    def _convert_messages_for_api(self) -> list[dict]:
        """Convert internal messages to API format."""
        api_messages = []

        for msg in self.messages:
            if msg["role"] == "user":
                api_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        content.append(
                            {
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": tc["name"],
                                "input": tc["arguments"],
                            }
                        )
                api_messages.append({"role": "assistant", "content": content})
            elif msg["role"] == "tool":
                # Tool results need to be in user message with tool_result type
                # Find if there's already a user message with tool results
                if (
                    api_messages
                    and api_messages[-1]["role"] == "user"
                    and isinstance(api_messages[-1]["content"], list)
                    and api_messages[-1]["content"]
                    and api_messages[-1]["content"][0].get("type") == "tool_result"
                ):
                    api_messages[-1]["content"].append(
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": str(msg["content"]),
                        }
                    )
                else:
                    api_messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": msg["tool_call_id"],
                                    "content": str(msg["content"]),
                                }
                            ],
                        }
                    )

        return api_messages

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """Run the agent with a user message, yielding events."""
        # Add user message
        self.messages.append({"role": "user", "content": user_message})

        yield AgentEvent(type="thinking", content="Processing your request...")

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # Call the model
            try:
                response = await self.model.call(
                    messages=self._convert_messages_for_api(),
                    tools=self.tool_manager.get_tool_definitions(),
                    system=self.system_prompt,
                )
            except Exception as e:
                yield AgentEvent(type="error", content=str(e))
                return

            # Emit text content
            if response.content:
                yield AgentEvent(type="text", content=response.content)

            # Add assistant message
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if response.content:
                assistant_msg["content"] = response.content
            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in response.tool_calls
                ]
            self.messages.append(assistant_msg)

            # If no tool calls, we're done
            if not response.has_tool_calls:
                yield AgentEvent(type="done", content=response.content)
                return

            # Process tool calls
            for tool_call in response.tool_calls:
                # Emit tool call event
                requires_confirm = self.tool_manager.requires_confirmation(tool_call.name)
                # Skip confirmation if user already allowed all for this tool
                if tool_call.name in self.auto_allowed_tools:
                    requires_confirm = False

                yield AgentEvent(
                    type="tool_call",
                    tool_name=tool_call.name,
                    tool_args=tool_call.arguments,
                    tool_call_id=tool_call.id,
                    requires_confirmation=requires_confirm,
                )

                # Request confirmation if needed
                if requires_confirm:
                    yield AgentEvent(
                        type="confirm_request",
                        tool_name=tool_call.name,
                        tool_args=tool_call.arguments,
                        tool_call_id=tool_call.id,
                    )

                    # Wait for confirmation
                    if self.confirm_callback:
                        allowed = await self.confirm_callback(
                            tool_call.id,
                            tool_call.name,
                            tool_call.arguments,
                        )
                        if not allowed:
                            # User denied, add a denial message
                            self.messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": "User denied this tool execution.",
                                }
                            )
                            yield AgentEvent(
                                type="tool_result",
                                tool_call_id=tool_call.id,
                                content={"denied": True},
                            )
                            continue

                # Execute the tool
                result = await self.tool_manager.execute(
                    tool_call.name,
                    tool_call.arguments,
                )

                # Add tool result to messages
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result.output) if result.success else str(result.error),
                    }
                )

                yield AgentEvent(
                    type="tool_result",
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    content=result.to_dict(),
                )

        # Max iterations reached
        yield AgentEvent(
            type="error",
            content=f"Agent reached maximum iterations ({self.max_iterations})",
        )

    def allow_tool_for_session(self, tool_name: str) -> None:
        """Allow a tool for the rest of the session without confirmation."""
        self.auto_allowed_tools.add(tool_name)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []
        self.auto_allowed_tools = set()
