"""Multi-model router for Honolulu."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator

from honolulu.models.base import ModelProvider, ModelResponse, StreamChunk


class RoutingStrategy(Enum):
    """Model routing strategies."""

    COST_OPTIMIZED = "cost-optimized"      # Prefer cheaper models
    QUALITY_FIRST = "quality-first"        # Prefer highest quality
    ROUND_ROBIN = "round-robin"            # Rotate between models
    CAPABILITY_MATCH = "capability-match"  # Match to task requirements
    SMART = "smart"                        # AI-based selection


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""

    name: str
    provider: ModelProvider
    priority: int = 0
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    capabilities: list[str] = field(default_factory=list)


class ModelRouter:
    """Routes requests to appropriate model providers."""

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.QUALITY_FIRST,
        fallback_enabled: bool = True,
    ):
        self._providers: dict[str, ProviderConfig] = {}
        self._strategy = strategy
        self._fallback_enabled = fallback_enabled
        self._round_robin_index = 0
        self._default_provider: str | None = None

    def register(
        self,
        name: str,
        provider: ModelProvider,
        priority: int = 0,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
        capabilities: list[str] | None = None,
        is_default: bool = False,
    ) -> None:
        """Register a model provider."""
        self._providers[name] = ProviderConfig(
            name=name,
            provider=provider,
            priority=priority,
            cost_per_1k_input=cost_per_1k_input,
            cost_per_1k_output=cost_per_1k_output,
            capabilities=capabilities or [],
        )

        if is_default or self._default_provider is None:
            self._default_provider = name

    def _select_provider(self, task_hint: str | None = None) -> ProviderConfig:
        """Select a provider based on strategy."""
        if not self._providers:
            raise ValueError("No providers registered")

        providers = list(self._providers.values())

        if self._strategy == RoutingStrategy.COST_OPTIMIZED:
            # Sort by cost (input + output)
            providers.sort(key=lambda p: p.cost_per_1k_input + p.cost_per_1k_output)
            return providers[0]

        elif self._strategy == RoutingStrategy.QUALITY_FIRST:
            # Sort by priority (higher = better)
            providers.sort(key=lambda p: p.priority, reverse=True)
            return providers[0]

        elif self._strategy == RoutingStrategy.ROUND_ROBIN:
            # Rotate through providers
            provider = providers[self._round_robin_index % len(providers)]
            self._round_robin_index += 1
            return provider

        elif self._strategy == RoutingStrategy.CAPABILITY_MATCH:
            # Match capabilities to task
            if task_hint:
                for p in providers:
                    if any(cap in task_hint.lower() for cap in p.capabilities):
                        return p
            # Fall back to default
            if self._default_provider:
                return self._providers[self._default_provider]
            return providers[0]

        else:  # SMART or default
            # Use default provider
            if self._default_provider:
                return self._providers[self._default_provider]
            return providers[0]

    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        task_hint: str | None = None,
    ) -> ModelResponse:
        """Route and make a model call with fallback."""
        selected = self._select_provider(task_hint)
        providers_tried = [selected.name]

        try:
            return await selected.provider.call(
                messages=messages,
                tools=tools,
                system=system,
                max_tokens=max_tokens,
            )
        except Exception as e:
            if not self._fallback_enabled:
                raise

            # Try other providers
            for name, config in self._providers.items():
                if name in providers_tried:
                    continue

                providers_tried.append(name)
                try:
                    return await config.provider.call(
                        messages=messages,
                        tools=tools,
                        system=system,
                        max_tokens=max_tokens,
                    )
                except Exception:
                    continue

            # All providers failed
            raise RuntimeError(
                f"All providers failed. Tried: {providers_tried}. Last error: {e}"
            )

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        task_hint: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Route and stream from a model."""
        selected = self._select_provider(task_hint)

        async for chunk in selected.provider.stream(
            messages=messages,
            tools=tools,
            system=system,
            max_tokens=max_tokens,
        ):
            yield chunk

    @property
    def providers(self) -> list[str]:
        """List registered provider names."""
        return list(self._providers.keys())
