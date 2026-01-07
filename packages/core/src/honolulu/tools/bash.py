"""Bash execution tool."""

import asyncio
import shlex
from typing import Any

from honolulu.tools.base import Tool, ToolResult


class BashExecTool(Tool):
    """Execute bash commands."""

    name = "bash_exec"
    description = "Execute a bash command and return the output. Use for running shell commands, scripts, or system operations."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 60)",
                "default": 60,
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command",
            },
        },
        "required": ["command"],
    }
    requires_confirmation = True

    async def execute(
        self,
        command: str,
        timeout: int = 60,
        cwd: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Command timed out after {timeout} seconds",
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "return_code": process.returncode,
                    },
                )
            else:
                return ToolResult(
                    success=False,
                    output={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "return_code": process.returncode,
                    },
                    error=f"Command exited with code {process.returncode}",
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


def get_bash_tools() -> list[Tool]:
    """Get all bash tools."""
    return [BashExecTool()]
