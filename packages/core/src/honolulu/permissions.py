"""Permission controller for tool execution."""

import fnmatch
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PermissionConfig:
    """Configuration for permission controller."""

    mode: str = "interactive"  # "auto", "interactive", "strict"

    # Allowed paths (glob patterns)
    allowed_paths: list[str] = field(default_factory=list)

    # Blocked paths (glob patterns)
    blocked_paths: list[str] = field(default_factory=list)

    # Allowed command prefixes
    allowed_commands: list[str] = field(default_factory=list)

    # Blocked commands (exact match or pattern)
    blocked_commands: list[str] = field(default_factory=list)


class PermissionController:
    """Controls whether tool executions are allowed."""

    def __init__(self, config: PermissionConfig | None = None):
        self.config = config or PermissionConfig()
        self._expand_paths()

    def _expand_paths(self) -> None:
        """Expand environment variables in paths."""
        self.config.allowed_paths = [
            self._expand_env(p) for p in self.config.allowed_paths
        ]
        self.config.blocked_paths = [
            self._expand_env(p) for p in self.config.blocked_paths
        ]

    def _expand_env(self, path: str) -> str:
        """Expand ${VAR} style environment variables."""
        pattern = r"\$\{([^}]+)\}"

        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        return re.sub(pattern, replace, path)

    def is_path_allowed(self, path: str) -> tuple[bool, str | None]:
        """Check if a path is allowed for file operations."""
        try:
            resolved = Path(path).expanduser().resolve()
            path_str = str(resolved)
        except Exception as e:
            return False, f"Invalid path: {e}"

        # Check blocked paths first
        for pattern in self.config.blocked_paths:
            expanded_pattern = str(Path(pattern).expanduser())
            if fnmatch.fnmatch(path_str, expanded_pattern):
                return False, f"Path matches blocked pattern: {pattern}"

        # If allowed_paths is specified, path must match at least one
        if self.config.allowed_paths:
            for pattern in self.config.allowed_paths:
                expanded_pattern = str(Path(pattern).expanduser())
                if fnmatch.fnmatch(path_str, expanded_pattern):
                    return True, None

            return False, "Path not in allowed paths list"

        # No restrictions
        return True, None

    def is_command_allowed(self, command: str) -> tuple[bool, str | None]:
        """Check if a bash command is allowed."""
        command_lower = command.lower().strip()

        # Check blocked commands first
        for blocked in self.config.blocked_commands:
            if blocked.lower() in command_lower:
                return False, f"Command contains blocked pattern: {blocked}"

        # Check dangerous patterns
        dangerous_patterns = [
            r"rm\s+-rf\s+/(?!\w)",  # rm -rf / (but allow rm -rf /tmp/something)
            r":\(\)\{:\|:&\};:",  # Fork bomb
            r">\s*/dev/sd[a-z]",  # Write to disk devices
            r"mkfs\.",  # Format filesystem
            r"dd\s+.*of=/dev/",  # dd to device
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                return False, f"Command matches dangerous pattern"

        # If allowed_commands is specified, command must start with one
        if self.config.allowed_commands:
            command_parts = command.split()
            if command_parts:
                first_word = command_parts[0]
                for allowed in self.config.allowed_commands:
                    if first_word == allowed or first_word.endswith(f"/{allowed}"):
                        return True, None

            return False, "Command not in allowed commands list"

        return True, None

    def check_tool_permission(
        self,
        tool_name: str,
        params: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Check if a tool execution is allowed."""
        # Auto mode: always allow
        if self.config.mode == "auto":
            return True, None

        # Check path-based tools
        if tool_name in ("file_read", "file_write", "file_list"):
            path = params.get("path", "")
            allowed, reason = self.is_path_allowed(path)
            if not allowed:
                return False, reason

        # Check bash command
        if tool_name == "bash_exec":
            command = params.get("command", "")
            allowed, reason = self.is_command_allowed(command)
            if not allowed:
                return False, reason

        return True, None

    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if a tool requires user confirmation."""
        if self.config.mode == "auto":
            return False

        if self.config.mode == "strict":
            return True

        # Interactive mode: check tool type
        confirmation_required = {
            "file_write",
            "bash_exec",
            "mcp_call",
        }

        return tool_name in confirmation_required
