"""Configuration management."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from honolulu.permissions import PermissionConfig


@dataclass
class ModelConfig:
    """Model configuration."""

    provider: str = "anthropic"
    name: str = "claude-sonnet-4-20250514"
    api_key: str = "${ANTHROPIC_API_KEY}"
    base_url: str | None = None
    max_tokens: int = 8192


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "127.0.0.1"
    port: int = 8420


@dataclass
class MCPServerConfig:
    """MCP server configuration."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    """Main configuration."""

    agent_name: str = "honolulu"
    model: ModelConfig = field(default_factory=ModelConfig)
    permissions: PermissionConfig = field(default_factory=PermissionConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data or {})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create config from a dictionary."""
        config = cls()

        if "agent" in data:
            config.agent_name = data["agent"].get("name", config.agent_name)

        if "model" in data:
            model_data = data["model"]
            config.model = ModelConfig(
                provider=model_data.get("provider", "anthropic"),
                name=model_data.get("name", "claude-sonnet-4-20250514"),
                api_key=model_data.get("api_key", "${ANTHROPIC_API_KEY}"),
                base_url=model_data.get("base_url"),
                max_tokens=model_data.get("max_tokens", 8192),
            )

        if "permissions" in data:
            perm_data = data["permissions"]
            config.permissions = PermissionConfig(
                mode=perm_data.get("mode", "interactive"),
                allowed_paths=perm_data.get("allowed_paths", []),
                blocked_paths=perm_data.get("blocked_paths", []),
                allowed_commands=perm_data.get("allowed_commands", []),
                blocked_commands=perm_data.get("blocked_commands", []),
            )

        if "server" in data:
            server_data = data["server"]
            config.server = ServerConfig(
                host=server_data.get("host", "127.0.0.1"),
                port=server_data.get("port", 8420),
            )

        if "mcp_servers" in data:
            for mcp_data in data["mcp_servers"]:
                config.mcp_servers.append(
                    MCPServerConfig(
                        name=mcp_data["name"],
                        command=mcp_data["command"],
                        args=mcp_data.get("args", []),
                        env=mcp_data.get("env", {}),
                    )
                )

        return config

    def expand_env_vars(self) -> None:
        """Expand environment variables in configuration."""
        self.model.api_key = self._expand_env(self.model.api_key)

        for mcp in self.mcp_servers:
            mcp.env = {k: self._expand_env(v) for k, v in mcp.env.items()}

    def _expand_env(self, value: str) -> str:
        """Expand ${VAR} style environment variables."""
        pattern = r"\$\{([^}]+)\}"

        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, "")

        return re.sub(pattern, replace, value)


def get_default_config() -> Config:
    """Get default configuration."""
    return Config(
        permissions=PermissionConfig(
            mode="interactive",
            allowed_paths=["${HOME}/projects/**", "/tmp/**"],
            blocked_paths=["${HOME}/.ssh/**", "${HOME}/.aws/**"],
            allowed_commands=["git", "ls", "cat", "npm", "python", "pip", "node"],
            blocked_commands=["rm -rf /", "sudo", "chmod 777"],
        )
    )
