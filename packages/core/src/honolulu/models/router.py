"""Multi-model router for intelligent model selection."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from honolulu.models.base import ModelProvider


class RoutingStrategy(str, Enum):
    """Model routing strategies."""

    COST_OPTIMIZED = "cost-optimized"
    QUALITY_FIRST = "quality-first"
    CAPABILITY_MATCH = "capability-match"
    LOAD_BALANCE = "load-balance"
    SMART = "smart"  # Combines multiple strategies


@dataclass
class ModelInfo:
    """Information about a model for routing decisions."""

    name: str
    provider: ModelProvider
    pricing_input: float = 0.0  # Cost per 1M input tokens
    pricing_output: float = 0.0  # Cost per 1M output tokens
    capabilities: set[str] = field(default_factory=set)
    # Capabilities: "vision", "code", "reasoning", "function_calling", "streaming"
    max_context: int = 128000
    priority: int = 0  # Higher = preferred


@dataclass
class RoutingRule:
    """A rule for routing based on task characteristics."""

    condition: str  # Simple expression like "task.type == 'code'"
    model_name: str
    priority: int = 0


class TaskAnalyzer:
    """Analyzes tasks to determine routing characteristics."""

    CODE_KEYWORDS = [
        "code", "programming", "function", "class", "debug", "fix",
        "implement", "refactor", "python", "javascript", "typescript",
        "java", "rust", "go", "c++", "sql", "api", "algorithm",
        "代码", "编程", "函数", "类", "调试", "修复", "实现", "重构"
    ]

    REASONING_KEYWORDS = [
        "why", "explain", "analyze", "compare", "evaluate", "reason",
        "think", "consider", "argue", "prove", "deduce",
        "为什么", "解释", "分析", "比较", "评估", "推理", "思考"
    ]

    SIMPLE_KEYWORDS = [
        "what is", "define", "list", "show", "tell me", "how many",
        "translate", "convert", "format",
        "什么是", "定义", "列出", "显示", "告诉我", "多少", "翻译", "转换"
    ]

    @classmethod
    def analyze(cls, message: str, context: list[dict] | None = None) -> dict[str, Any]:
        """Analyze a message to determine task characteristics."""
        message_lower = message.lower()

        # Detect task type
        task_type = "general"
        if any(kw in message_lower for kw in cls.CODE_KEYWORDS):
            task_type = "code"
        elif any(kw in message_lower for kw in cls.REASONING_KEYWORDS):
            task_type = "reasoning"
        elif any(kw in message_lower for kw in cls.SIMPLE_KEYWORDS):
            task_type = "simple"

        # Estimate complexity
        complexity = "medium"
        word_count = len(message.split())

        if word_count < 20 and task_type == "simple":
            complexity = "simple"
        elif word_count > 100 or task_type in ("code", "reasoning"):
            complexity = "complex"

        # Check for vision requirement (image URLs or base64)
        requires_vision = bool(
            re.search(r"(https?://\S+\.(png|jpg|jpeg|gif|webp))", message_lower)
            or "image" in message_lower
            or "图片" in message_lower
        )

        # Context length consideration
        context_tokens = 0
        if context:
            context_tokens = sum(
                len(str(m.get("content", ""))) // 4 for m in context
            )

        return {
            "type": task_type,
            "complexity": complexity,
            "requires_vision": requires_vision,
            "word_count": word_count,
            "context_tokens": context_tokens,
        }


class ModelRouter:
    """Routes requests to the most appropriate model."""

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.SMART,
        default_model: str | None = None,
    ):
        self.strategy = strategy
        self.default_model = default_model
        self.models: dict[str, ModelInfo] = {}
        self.rules: list[RoutingRule] = []
        self.fallback_order: list[str] = []
        self._usage_counts: dict[str, int] = {}

    def register_model(self, info: ModelInfo) -> None:
        """Register a model with the router."""
        self.models[info.name] = info
        self._usage_counts[info.name] = 0

        if not self.default_model:
            self.default_model = info.name

    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule."""
        self.rules.append(rule)
        # Sort by priority (higher first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def set_fallback_order(self, order: list[str]) -> None:
        """Set the fallback order for models."""
        self.fallback_order = order

    def select(
        self,
        message: str,
        context: list[dict] | None = None,
    ) -> ModelProvider:
        """Select the best model for the given task."""
        if not self.models:
            raise ValueError("No models registered with the router")

        task = TaskAnalyzer.analyze(message, context)

        # Try rule-based routing first
        for rule in self.rules:
            if self._evaluate_rule(rule.condition, task):
                if rule.model_name in self.models:
                    return self.models[rule.model_name].provider

        # Strategy-based selection
        selected_name = self._select_by_strategy(task)

        self._usage_counts[selected_name] = self._usage_counts.get(selected_name, 0) + 1

        return self.models[selected_name].provider

    def _evaluate_rule(self, condition: str, task: dict) -> bool:
        """Evaluate a simple rule condition."""
        # Support simple conditions like:
        # "task.type == 'code'"
        # "task.complexity == 'simple'"
        # "task.requires_vision == true"

        try:
            # Parse condition
            match = re.match(r"task\.(\w+)\s*==\s*['\"]?(\w+)['\"]?", condition)
            if match:
                key, value = match.groups()
                actual = task.get(key)

                if value.lower() == "true":
                    return actual is True
                elif value.lower() == "false":
                    return actual is False
                else:
                    return str(actual).lower() == value.lower()

            return False
        except Exception:
            return False

    def _select_by_strategy(self, task: dict) -> str:
        """Select a model based on the configured strategy."""
        if self.strategy == RoutingStrategy.COST_OPTIMIZED:
            return self._select_cheapest(task)
        elif self.strategy == RoutingStrategy.QUALITY_FIRST:
            return self._select_best_quality(task)
        elif self.strategy == RoutingStrategy.CAPABILITY_MATCH:
            return self._select_by_capability(task)
        elif self.strategy == RoutingStrategy.LOAD_BALANCE:
            return self._select_least_used()
        else:  # SMART
            return self._select_smart(task)

    def _select_cheapest(self, task: dict) -> str:
        """Select the cheapest model that meets requirements."""
        candidates = self._filter_capable(task)
        if not candidates:
            candidates = list(self.models.keys())

        # Sort by cost
        sorted_models = sorted(
            candidates,
            key=lambda n: (
                self.models[n].pricing_input + self.models[n].pricing_output
            ),
        )

        return sorted_models[0] if sorted_models else self.default_model or ""

    def _select_best_quality(self, task: dict) -> str:
        """Select the highest quality model."""
        candidates = self._filter_capable(task)
        if not candidates:
            candidates = list(self.models.keys())

        # Sort by priority (higher is better)
        sorted_models = sorted(
            candidates,
            key=lambda n: self.models[n].priority,
            reverse=True,
        )

        return sorted_models[0] if sorted_models else self.default_model or ""

    def _select_by_capability(self, task: dict) -> str:
        """Select the model with the best capability match."""
        required_caps = set()

        if task.get("requires_vision"):
            required_caps.add("vision")
        if task.get("type") == "code":
            required_caps.add("code")
        if task.get("type") == "reasoning":
            required_caps.add("reasoning")

        best_match = None
        best_score = -1

        for name, info in self.models.items():
            # Score = number of matching capabilities
            score = len(required_caps & info.capabilities)

            # Bonus for having function calling
            if "function_calling" in info.capabilities:
                score += 0.5

            if score > best_score:
                best_score = score
                best_match = name

        return best_match or self.default_model or ""

    def _select_least_used(self) -> str:
        """Select the least used model for load balancing."""
        if not self.models:
            return self.default_model or ""

        return min(self._usage_counts.items(), key=lambda x: x[1])[0]

    def _select_smart(self, task: dict) -> str:
        """Smart selection combining multiple factors."""
        # For simple tasks, prefer cheaper models
        if task.get("complexity") == "simple":
            return self._select_cheapest(task)

        # For complex code/reasoning, prefer quality
        if task.get("type") in ("code", "reasoning") or task.get("complexity") == "complex":
            return self._select_best_quality(task)

        # For vision tasks, filter by capability
        if task.get("requires_vision"):
            return self._select_by_capability(task)

        # Default to quality
        return self._select_best_quality(task)

    def _filter_capable(self, task: dict) -> list[str]:
        """Filter models by required capabilities."""
        required_caps = set()

        if task.get("requires_vision"):
            required_caps.add("vision")

        if not required_caps:
            return list(self.models.keys())

        return [
            name
            for name, info in self.models.items()
            if required_caps.issubset(info.capabilities)
        ]

    async def call_with_fallback(
        self,
        message: str,
        context: list[dict] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Call a model with automatic fallback on failure."""
        # Get ordered list of models to try
        primary = self.select(message, context)
        primary_name = next(
            (n for n, i in self.models.items() if i.provider is primary),
            None,
        )

        models_to_try = [primary_name] if primary_name else []
        models_to_try.extend(
            n for n in self.fallback_order if n not in models_to_try
        )
        models_to_try.extend(
            n for n in self.models.keys() if n not in models_to_try
        )

        last_error = None
        for model_name in models_to_try:
            if model_name not in self.models:
                continue

            try:
                provider = self.models[model_name].provider
                return await provider.call(**kwargs)
            except Exception as e:
                last_error = e
                print(f"Model {model_name} failed: {e}, trying next...")
                continue

        raise RuntimeError(f"All models failed. Last error: {last_error}")


def create_router_from_config(config: dict) -> ModelRouter:
    """Create a ModelRouter from configuration dictionary."""
    from honolulu.models.claude import ClaudeProvider
    from honolulu.models.openai_provider import OpenAIProvider

    strategy = RoutingStrategy(config.get("strategy", "smart"))
    router = ModelRouter(strategy=strategy, default_model=config.get("default"))

    # Register providers
    for provider_config in config.get("providers", []):
        name = provider_config["name"]
        provider_type = provider_config.get("provider", "anthropic")

        # Create provider instance
        if provider_type == "anthropic":
            provider = ClaudeProvider(
                api_key=provider_config.get("api_key"),
                model=provider_config.get("model", "claude-sonnet-4-20250514"),
                base_url=provider_config.get("base_url"),
            )
        elif provider_type in ("openai", "custom"):
            provider = OpenAIProvider(
                api_key=provider_config.get("api_key"),
                model=provider_config.get("model", "gpt-4o"),
                base_url=provider_config.get("base_url"),
            )
        else:
            continue

        # Parse capabilities
        capabilities = set(provider_config.get("features", []))

        # Parse pricing
        pricing = provider_config.get("pricing", {})

        info = ModelInfo(
            name=name,
            provider=provider,
            pricing_input=pricing.get("input", 0),
            pricing_output=pricing.get("output", 0),
            capabilities=capabilities,
            priority=provider_config.get("priority", 0),
        )

        router.register_model(info)

    # Add rules
    for rule_config in config.get("rules", []):
        router.add_rule(
            RoutingRule(
                condition=rule_config["condition"],
                model_name=rule_config["model"],
                priority=rule_config.get("priority", 0),
            )
        )

    # Set fallback order
    if "fallback" in config:
        router.set_fallback_order(config["fallback"])

    return router
