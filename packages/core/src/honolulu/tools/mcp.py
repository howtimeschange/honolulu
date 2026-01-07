"""MCP (Model Context Protocol) integration for external tool servers."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from honolulu.tools.base import Tool, ToolResult


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None  # For HTTP/SSE servers
    requires_confirmation: bool = True  # Default to requiring confirmation


class MCPTool(Tool):
    """A tool that wraps an MCP server tool."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        server_name: str,
        mcp_manager: "MCPManager",
        requires_confirmation: bool = True,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.server_name = server_name
        self.mcp_manager = mcp_manager
        self.requires_confirmation = requires_confirmation

    async def execute(self, **params: Any) -> ToolResult:
        """Execute the MCP tool."""
        try:
            result = await self.mcp_manager.call_tool(
                self.server_name,
                self.name,
                params,
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class MCPManager:
    """Manages connections to MCP servers."""

    def __init__(self):
        self._client = None
        self._sessions: dict[str, Any] = {}
        self._tools: dict[str, MCPTool] = {}
        self._configs: dict[str, MCPServerConfig] = {}
        self._initialized = False

    async def initialize(self, configs: list[MCPServerConfig]) -> None:
        """Initialize connections to all configured MCP servers."""
        if not configs:
            return

        try:
            from mcp_use import MCPClient
        except ImportError:
            raise ImportError(
                "mcp-use is not installed. Install it with: pip install mcp-use"
            )

        # Build configuration dictionary
        mcp_config: dict[str, Any] = {"mcpServers": {}}

        for config in configs:
            self._configs[config.name] = config

            server_config: dict[str, Any] = {}

            if config.url:
                # HTTP/SSE server
                server_config["url"] = config.url
            else:
                # Command-based server
                server_config["command"] = config.command
                server_config["args"] = config.args

            if config.env:
                server_config["env"] = config.env

            mcp_config["mcpServers"][config.name] = server_config

        # Create client and sessions
        self._client = MCPClient.from_dict(mcp_config)
        await self._client.create_all_sessions()

        # Discover tools from all servers
        await self._discover_tools()
        self._initialized = True

    async def _discover_tools(self) -> None:
        """Discover and register tools from all connected MCP servers."""
        if not self._client:
            return

        for server_name, config in self._configs.items():
            try:
                session = self._client.get_session(server_name)
                tools = await session.list_tools()

                for tool in tools:
                    # Convert MCP tool to our Tool format
                    tool_name = f"mcp_{server_name}_{tool.name}"

                    # Build JSON Schema from tool input schema
                    parameters = {}
                    if hasattr(tool, "inputSchema") and tool.inputSchema:
                        parameters = tool.inputSchema
                    elif hasattr(tool, "input_schema") and tool.input_schema:
                        parameters = tool.input_schema
                    else:
                        parameters = {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        }

                    mcp_tool = MCPTool(
                        name=tool_name,
                        description=tool.description or f"MCP tool: {tool.name}",
                        parameters=parameters,
                        server_name=server_name,
                        mcp_manager=self,
                        requires_confirmation=config.requires_confirmation,
                    )

                    # Store original name for calling
                    mcp_tool._original_name = tool.name
                    self._tools[tool_name] = mcp_tool

            except Exception as e:
                print(f"Warning: Failed to discover tools from {server_name}: {e}")

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a tool on an MCP server."""
        if not self._client:
            raise RuntimeError("MCP client not initialized")

        session = self._client.get_session(server_name)

        # Get original tool name (without prefix)
        original_name = tool_name
        if tool_name.startswith(f"mcp_{server_name}_"):
            original_name = tool_name[len(f"mcp_{server_name}_") :]

        result = await session.call_tool(name=original_name, arguments=arguments)

        # Extract content from result
        if hasattr(result, "content") and result.content:
            if len(result.content) == 1:
                content = result.content[0]
                if hasattr(content, "text"):
                    return content.text
                return str(content)
            return [str(c) for c in result.content]

        return str(result)

    def get_tools(self) -> list[MCPTool]:
        """Get all discovered MCP tools."""
        return list(self._tools.values())

    async def close(self) -> None:
        """Close all MCP server connections."""
        if self._client:
            await self._client.close_all_sessions()
            self._client = None
            self._sessions = {}
            self._tools = {}
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# Singleton instance
_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    """Get the global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


async def initialize_mcp_servers(configs: list[MCPServerConfig]) -> list[Tool]:
    """Initialize MCP servers and return discovered tools."""
    manager = get_mcp_manager()
    await manager.initialize(configs)
    return manager.get_tools()
