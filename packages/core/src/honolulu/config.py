"""Configuration management."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from honolulu.permissions import PermissionConfig


@dataclass
class ModelProviderConfig:
    """Configuration for a single model provider."""

    name: str
    provider: str  # "anthropic", "openai", "custom"
    model: str
    api_key: str
    base_url: str | None = None
    pricing_input: float = 0.0
    pricing_output: float = 0.0
    features: list[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class RoutingRuleConfig:
    """Configuration for a routing rule."""

    condition: str
    model: str
    priority: int = 0


@dataclass
class RoutingConfig:
    """Configuration for model routing."""

    strategy: str = "smart"  # "cost-optimized", "quality-first", "capability-match", "smart"
    default: str | None = None
    providers: list[ModelProviderConfig] = field(default_factory=list)
    rules: list[RoutingRuleConfig] = field(default_factory=list)
    fallback: list[str] = field(default_factory=list)


@dataclass
class ModelConfig:
    """Model configuration (legacy single-model config)."""

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
    vector_store: str = "chroma"  # "chroma" | "in_memory"
    persist_directory: str | None = None  # Path for persistent storage
    embedding_model: str = "all-MiniLM-L6-v2"
    compression_threshold: int = 100000  # tokens


@dataclass
class Config:
    """Main configuration."""

    agent_name: str = "honolulu"
    model: ModelConfig = field(default_factory=ModelConfig)
    routing: RoutingConfig | None = None  # Multi-model routing config
    memory: MemoryConfig = field(default_factory=MemoryConfig)
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

        if "memory" in data:
            mem_data = data["memory"]
            config.memory = MemoryConfig(
                enabled=mem_data.get("enabled", True),
                short_term_limit=mem_data.get("short_term_limit", 50),
                vector_store=mem_data.get("vector_store", "chroma"),
                persist_directory=mem_data.get("persist_directory"),
                embedding_model=mem_data.get("embedding_model", "all-MiniLM-L6-v2"),
                compression_threshold=mem_data.get("compression_threshold", 100000),
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

        # Parse routing configuration
        if "routing" in data:
            routing_data = data["routing"]
            providers = []
            for p in routing_data.get("providers", []):
                pricing = p.get("pricing", {})
                providers.append(
                    ModelProviderConfig(
                        name=p["name"],
                        provider=p.get("provider", "anthropic"),
                        model=p.get("model", ""),
                        api_key=p.get("api_key", ""),
                        base_url=p.get("base_url"),
                        pricing_input=pricing.get("input", 0),
                        pricing_output=pricing.get("output", 0),
                        features=p.get("features", []),
                        priority=p.get("priority", 0),
                    )
                )

            rules = []
            for r in routing_data.get("rules", []):
                rules.append(
                    RoutingRuleConfig(
                        condition=r["condition"],
                        model=r["model"],
                        priority=r.get("priority", 0),
                    )
                )

            config.routing = RoutingConfig(
                strategy=routing_data.get("strategy", "smart"),
                default=routing_data.get("default"),
                providers=providers,
                rules=rules,
                fallback=routing_data.get("fallback", []),
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

        # Expand routing provider API keys and base_urls
        if self.routing:
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
