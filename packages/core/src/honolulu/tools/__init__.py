"""Tool system for Honolulu agent."""

from honolulu.tools.base import Tool, ToolResult, ToolManager
from honolulu.tools.file_ops import get_file_tools
from honolulu.tools.bash import get_bash_tools
from honolulu.tools.web import get_web_tools
from honolulu.tools.mcp import (
    MCPManager,
    MCPServerConfig,
    MCPTool,
    get_mcp_manager,
    initialize_mcp_servers,
)


def get_builtin_tools() -> list[Tool]:
    """Get all built-in tools."""
    return get_file_tools() + get_bash_tools() + get_web_tools()


__all__ = [
    "Tool",
    "ToolResult",
    "ToolManager",
    "get_builtin_tools",
    "MCPManager",
    "MCPServerConfig",
    "MCPTool",
    "get_mcp_manager",
    "initialize_mcp_servers",
]
