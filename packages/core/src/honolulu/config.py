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
class MemoryConfig:
    """Memory system configuration."""

    enabled: bool = True
    short_term_limit: int = 50
    vector_store: str = "in_memory"  # "chroma" | "in_memory"
    persist_directory: str | None = None


@dataclass
class ProviderConfig:
    """Model provider configuration for multi-model routing."""

    name: str
    type: str  # "anthropic" | "openai"
    api_key: str
    model: str
    base_url: str | None = None
    priority: int = 0
    is_default: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    capabilities: list[str] = field(default_factory=list)


@dataclass
class RoutingConfig:
    """Multi-model routing configuration."""

    enabled: bool = False
    strategy: str = "quality-first"  # cost-optimized, quality-first, round-robin
    fallback_enabled: bool = True
    providers: list[ProviderConfig] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration."""

    agent_name: str = "honolulu"
    model: ModelConfig = field(default_factory=ModelConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
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

        if "memory" in data:
            memory_data = data["memory"]
            config.memory = MemoryConfig(
                enabled=memory_data.get("enabled", True),
                short_term_limit=memory_data.get("short_term_limit", 50),
                vector_store=memory_data.get("vector_store", "in_memory"),
                persist_directory=memory_data.get("persist_directory"),
            )

        if "routing" in data:
            routing_data = data["routing"]
            providers = []
            for p in routing_data.get("providers", []):
                providers.append(
                    ProviderConfig(
                        name=p["name"],
                        type=p["type"],
                        api_key=p.get("api_key", ""),
                        model=p["model"],
                        base_url=p.get("base_url"),
                        priority=p.get("priority", 0),
                        is_default=p.get("is_default", False),
                        cost_per_1k_input=p.get("cost_per_1k_input", 0.0),
                        cost_per_1k_output=p.get("cost_per_1k_output", 0.0),
                        capabilities=p.get("capabilities", []),
                    )
                )
            config.routing = RoutingConfig(
                enabled=routing_data.get("enabled", False),
                strategy=routing_data.get("strategy", "quality-first"),
                fallback_enabled=routing_data.get("fallback_enabled", True),
                providers=providers,
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

        # Expand base_url (for OneRouter, OpenRouter, etc.)
        if self.model.base_url:
            expanded = self._expand_env(self.model.base_url)
            # Set to None if empty (not configured)
            self.model.base_url = expanded if expanded else None

        # Expand provider configs
        for provider in self.routing.providers:
            provider.api_key = self._expand_env(provider.api_key)
            if provider.base_url:
                expanded = self._expand_env(provider.base_url)
                provider.base_url = expanded if expanded else None

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
