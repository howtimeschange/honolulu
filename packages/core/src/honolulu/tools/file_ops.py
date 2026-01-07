"""File operation tools."""

import os
from pathlib import Path
from typing import Any

import aiofiles

from honolulu.tools.base import Tool, ToolResult


class FileReadTool(Tool):
    """Read file contents."""

    name = "file_read"
    description = "Read the contents of a file at the specified path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to read",
            },
        },
        "required": ["path"],
    }
    requires_confirmation = False

    async def execute(self, path: str, **kwargs: Any) -> ToolResult:
        try:
            resolved_path = Path(path).expanduser().resolve()
            if not resolved_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {path}",
                )

            if not resolved_path.is_file():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a file: {path}",
                )

            async with aiofiles.open(resolved_path, "r", encoding="utf-8") as f:
                content = await f.read()

            return ToolResult(
                success=True,
                output=content,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


class FileWriteTool(Tool):
    """Write content to a file."""

    name = "file_write"
    description = "Write content to a file at the specified path. Creates the file if it doesn't exist."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
        },
        "required": ["path", "content"],
    }
    requires_confirmation = True

    async def execute(self, path: str, content: str, **kwargs: Any) -> ToolResult:
        try:
            resolved_path = Path(path).expanduser().resolve()

            # Create parent directories if they don't exist
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(resolved_path, "w", encoding="utf-8") as f:
                await f.write(content)

            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


class FileListTool(Tool):
    """List directory contents."""

    name = "file_list"
    description = "List the contents of a directory."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the directory to list",
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to list recursively",
                "default": False,
            },
        },
        "required": ["path"],
    }
    requires_confirmation = False

    async def execute(
        self, path: str, recursive: bool = False, **kwargs: Any
    ) -> ToolResult:
        try:
            resolved_path = Path(path).expanduser().resolve()
            if not resolved_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Directory not found: {path}",
                )

            if not resolved_path.is_dir():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a directory: {path}",
                )

            if recursive:
                entries = []
                for root, dirs, files in os.walk(resolved_path):
                    rel_root = Path(root).relative_to(resolved_path)
                    for d in dirs:
                        entries.append(
                            {"name": str(rel_root / d), "type": "directory"}
                        )
                    for f in files:
                        entries.append({"name": str(rel_root / f), "type": "file"})
            else:
                entries = []
                for entry in resolved_path.iterdir():
                    entries.append(
                        {
                            "name": entry.name,
                            "type": "directory" if entry.is_dir() else "file",
                        }
                    )

            return ToolResult(
                success=True,
                output=entries,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


def get_file_tools() -> list[Tool]:
    """Get all file operation tools."""
    return [FileReadTool(), FileWriteTool(), FileListTool()]
