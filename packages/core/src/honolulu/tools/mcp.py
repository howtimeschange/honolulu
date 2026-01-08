"""MCP server integration for Honolulu."""

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


class MCPTool(Tool):
    """A tool that wraps an MCP server tool."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        server_name: str,
        call_func: Any,
    ):
        self.name = f"mcp_{server_name}_{name}"
        self.description = f"[MCP:{server_name}] {description}"
        self.parameters = parameters
        self.requires_confirmation = True  # MCP tools require confirmation
        self._server_name = server_name
        self._call_func = call_func

    async def execute(self, **params: Any) -> ToolResult:
        """Execute the MCP tool."""
        try:
            result = await self._call_func(**params)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class MCPManager:
    """Manages connections to MCP servers."""

    def __init__(self):
        self._servers: dict[str, Any] = {}
        self._tools: list[Tool] = []
        self._initialized = False

    async def initialize(self, configs: list[MCPServerConfig]) -> None:
        """Initialize connections to MCP servers."""
        if self._initialized:
            return

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            print("Warning: mcp package not installed. MCP features disabled.")
            print("Install with: pip install honolulu[mcp]")
            self._initialized = True
            return

        for config in configs:
            try:
                server_params = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env or None,
                )

                # Create client session
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Initialize the session
                        await session.initialize()

                        # Get available tools
                        tools_response = await session.list_tools()

                        for tool in tools_response.tools:
                            mcp_tool = MCPTool(
                                name=tool.name,
                                description=tool.description or "",
                                parameters=tool.inputSchema or {
                                    "type": "object",
                                    "properties": {},
                                },
                                server_name=config.name,
                                call_func=lambda s=session, t=tool.name, **p: s.call_tool(t, p),
                            )
                            self._tools.append(mcp_tool)

                        self._servers[config.name] = session
                        print(
                            f"Connected to MCP server '{config.name}' "
                            f"with {len(tools_response.tools)} tools"
                        )

            except Exception as e:
                print(f"Warning: Failed to connect to MCP server '{config.name}': {e}")

        self._initialized = True

    def get_tools(self) -> list[Tool]:
        """Get all MCP tools."""
        return self._tools

    async def close(self) -> None:
        """Close all MCP server connections."""
        # Sessions are auto-closed by context manager
        self._servers.clear()
        self._tools.clear()
        self._initialized = False


# Global MCP manager instance
_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    """Get the global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
