# Missing Features Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the three missing core features: MCP integration, Memory system, and Multi-model routing.

**Architecture:**
- MCP: Use `mcp` Python package to connect to MCP servers, discover tools, and register them with ToolManager
- Memory: Create a simple memory system with short-term (in-memory list) and long-term (ChromaDB vector store) components
- Routing: Create ModelRouter that selects providers based on configured strategy

**Tech Stack:** Python 3.11+, mcp, chromadb, sentence-transformers, openai (for OpenAI-compatible providers)

---

## Phase 1: MCP Integration

### Task 1: Add MCP Dependencies

**Files:**
- Modify: `packages/core/pyproject.toml`

**Step 1: Add mcp to optional dependencies**

Edit `packages/core/pyproject.toml` to add:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.7.0",
]
mcp = [
    "mcp>=1.0.0",
]
memory = [
    "chromadb>=0.5.0",
    "sentence-transformers>=2.0.0",
]
routing = [
    "openai>=1.0.0",
]
all = [
    "honolulu[mcp,memory,routing]",
]
```

**Step 2: Commit**

```bash
git add packages/core/pyproject.toml
git commit -m "feat: add optional dependencies for mcp, memory, routing"
```

---

### Task 2: Create MCP Tool Wrapper

**Files:**
- Create: `packages/core/src/honolulu/tools/mcp.py`

**Step 1: Create MCP integration module**

Create `packages/core/src/honolulu/tools/mcp.py`:

```python
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
                                parameters=tool.inputSchema or {"type": "object", "properties": {}},
                                server_name=config.name,
                                call_func=lambda **p, s=session, t=tool.name: s.call_tool(t, p),
                            )
                            self._tools.append(mcp_tool)

                        self._servers[config.name] = session
                        print(f"Connected to MCP server '{config.name}' with {len(tools_response.tools)} tools")

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
```

**Step 2: Commit**

```bash
git add packages/core/src/honolulu/tools/mcp.py
git commit -m "feat: add MCP server integration"
```

---

### Task 3: Update Tools Module Exports

**Files:**
- Modify: `packages/core/src/honolulu/tools/__init__.py`

**Step 1: Add MCP exports**

Update `packages/core/src/honolulu/tools/__init__.py`:

```python
"""Tool system for Honolulu agent."""

from honolulu.tools.base import Tool, ToolResult, ToolManager
from honolulu.tools.file_ops import get_file_tools
from honolulu.tools.bash import get_bash_tools
from honolulu.tools.web import get_web_tools
from honolulu.tools.mcp import MCPManager, MCPServerConfig, MCPTool, get_mcp_manager


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
]
```

**Step 2: Commit**

```bash
git add packages/core/src/honolulu/tools/__init__.py
git commit -m "feat: export MCP tools from tools module"
```

---

### Task 4: Integrate MCP into Server

**Files:**
- Modify: `packages/core/src/honolulu/server/app.py`

**Step 1: Update imports and lifespan**

In `packages/core/src/honolulu/server/app.py`, update to initialize MCP:

Add import:
```python
from honolulu.tools import ToolManager, get_builtin_tools, MCPServerConfig, get_mcp_manager
```

Update lifespan function:
```python
# Global state
sessions: dict[str, Session] = {}
config: Config = get_default_config()
mcp_tools: list = []  # MCP tools discovered at startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global config, mcp_tools

    # Load config if file exists
    config_path = Path("config/default.yaml")
    if config_path.exists():
        config = Config.load(config_path)

    config.expand_env_vars()

    # Initialize MCP servers if configured
    if config.mcp_servers:
        try:
            mcp_configs = [
                MCPServerConfig(
                    name=s.name,
                    command=s.command,
                    args=s.args,
                    env=s.env,
                )
                for s in config.mcp_servers
            ]
            mcp_manager = get_mcp_manager()
            await mcp_manager.initialize(mcp_configs)
            mcp_tools = mcp_manager.get_tools()
            print(f"Initialized {len(mcp_tools)} MCP tools")
        except Exception as e:
            print(f"Warning: Failed to initialize MCP servers: {e}")

    yield

    # Cleanup MCP connections
    try:
        mcp_manager = get_mcp_manager()
        await mcp_manager.close()
    except Exception:
        pass

    # Cleanup sessions
    sessions.clear()
```

Update create_agent function:
```python
def create_agent() -> Agent:
    """Create a new agent instance."""
    # Create model provider
    model = ClaudeProvider(
        api_key=config.model.api_key,
        model=config.model.name,
        base_url=config.model.base_url,
    )

    # Create tool manager with built-in tools
    tool_manager = ToolManager()
    tool_manager.register_all(get_builtin_tools())

    # Register MCP tools if available
    if mcp_tools:
        tool_manager.register_all(mcp_tools)

    # Create agent
    return Agent(model=model, tool_manager=tool_manager)
```

**Step 2: Commit**

```bash
git add packages/core/src/honolulu/server/app.py
git commit -m "feat: integrate MCP tools into server startup"
```

---

## Phase 2: Memory System

### Task 5: Create Memory Base Module

**Files:**
- Create: `packages/core/src/honolulu/memory/__init__.py`
- Create: `packages/core/src/honolulu/memory/base.py`

**Step 1: Create memory package**

Create `packages/core/src/honolulu/memory/__init__.py`:

```python
"""Memory system for Honolulu agent."""

from honolulu.memory.base import Memory, MemoryType, MemoryManager

__all__ = ["Memory", "MemoryType", "MemoryManager"]
```

**Step 2: Create memory base module**

Create `packages/core/src/honolulu/memory/base.py`:

```python
"""Base memory classes for Honolulu agent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(Enum):
    """Types of memory."""

    CONVERSATION = "conversation"  # Chat messages
    TASK = "task"                  # Task context
    KNOWLEDGE = "knowledge"        # Learned facts
    TOOL_RESULT = "tool_result"    # Tool execution results


@dataclass
class Memory:
    """A single memory entry."""

    content: str
    memory_type: MemoryType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class MemoryManager:
    """Manages short-term and long-term memory."""

    def __init__(
        self,
        short_term_limit: int = 50,
        vector_store: Any = None,
    ):
        self._short_term: list[Memory] = []
        self._short_term_limit = short_term_limit
        self._vector_store = vector_store

    def add(self, memory: Memory) -> None:
        """Add a memory to short-term storage."""
        self._short_term.append(memory)

        # Trim if over limit
        if len(self._short_term) > self._short_term_limit:
            # Move oldest to long-term if vector store available
            oldest = self._short_term.pop(0)
            if self._vector_store:
                self._vector_store.add(oldest)

    def add_message(self, role: str, content: str) -> None:
        """Add a conversation message to memory."""
        self.add(Memory(
            content=f"{role}: {content}",
            memory_type=MemoryType.CONVERSATION,
            metadata={"role": role},
        ))

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Add a tool result to memory."""
        self.add(Memory(
            content=f"Tool {tool_name} returned: {result}",
            memory_type=MemoryType.TOOL_RESULT,
            metadata={"tool": tool_name},
        ))

    def get_recent(self, limit: int = 10) -> list[Memory]:
        """Get recent memories from short-term storage."""
        return self._short_term[-limit:]

    def get_context(self, max_tokens: int = 4000) -> str:
        """Get memory context as a string for the model."""
        memories = self.get_recent(20)
        context_parts = []

        for mem in memories:
            context_parts.append(mem.content)

        return "\n".join(context_parts)

    async def search(self, query: str, limit: int = 5) -> list[Memory]:
        """Search long-term memory using vector similarity."""
        if not self._vector_store:
            return []

        return await self._vector_store.search(query, limit)

    def clear_short_term(self) -> None:
        """Clear short-term memory."""
        self._short_term.clear()

    @property
    def short_term_count(self) -> int:
        """Get count of short-term memories."""
        return len(self._short_term)
```

**Step 3: Commit**

```bash
git add packages/core/src/honolulu/memory/
git commit -m "feat: add memory system base classes"
```

---

### Task 6: Create Vector Store

**Files:**
- Create: `packages/core/src/honolulu/memory/vector_store.py`

**Step 1: Create vector store module**

Create `packages/core/src/honolulu/memory/vector_store.py`:

```python
"""Vector store for long-term memory."""

from typing import Any
from honolulu.memory.base import Memory, MemoryType


class VectorStore:
    """Base class for vector stores."""

    async def add(self, memory: Memory) -> None:
        """Add a memory to the store."""
        raise NotImplementedError

    async def search(self, query: str, limit: int = 5) -> list[Memory]:
        """Search for similar memories."""
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    """ChromaDB-based vector store."""

    def __init__(
        self,
        collection_name: str = "honolulu_memory",
        persist_directory: str | None = None,
    ):
        self._collection_name = collection_name
        self._persist_directory = persist_directory
        self._collection: Any = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB is initialized."""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "chromadb not installed. Install with: pip install honolulu[memory]"
            )

        if self._persist_directory:
            self._client = chromadb.PersistentClient(
                path=self._persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )
        else:
            self._client = chromadb.Client(
                settings=Settings(anonymized_telemetry=False),
            )

        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._initialized = True

    async def add(self, memory: Memory) -> None:
        """Add a memory to ChromaDB."""
        self._ensure_initialized()

        doc_id = f"{memory.memory_type.value}_{memory.timestamp.timestamp()}"

        self._collection.add(
            documents=[memory.content],
            metadatas=[{
                "type": memory.memory_type.value,
                "timestamp": memory.timestamp.isoformat(),
                **memory.metadata,
            }],
            ids=[doc_id],
        )

    async def search(self, query: str, limit: int = 5) -> list[Memory]:
        """Search for similar memories in ChromaDB."""
        self._ensure_initialized()

        results = self._collection.query(
            query_texts=[query],
            n_results=limit,
        )

        memories = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                memories.append(Memory(
                    content=doc,
                    memory_type=MemoryType(metadata.get("type", "knowledge")),
                    metadata=metadata,
                ))

        return memories


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store for testing."""

    def __init__(self):
        self._memories: list[Memory] = []

    async def add(self, memory: Memory) -> None:
        """Add a memory."""
        self._memories.append(memory)

    async def search(self, query: str, limit: int = 5) -> list[Memory]:
        """Simple keyword search (no actual vector similarity)."""
        query_lower = query.lower()
        matches = [
            m for m in self._memories
            if query_lower in m.content.lower()
        ]
        return matches[:limit]
```

**Step 2: Update memory exports**

Update `packages/core/src/honolulu/memory/__init__.py`:

```python
"""Memory system for Honolulu agent."""

from honolulu.memory.base import Memory, MemoryType, MemoryManager
from honolulu.memory.vector_store import VectorStore, ChromaVectorStore, InMemoryVectorStore

__all__ = [
    "Memory",
    "MemoryType",
    "MemoryManager",
    "VectorStore",
    "ChromaVectorStore",
    "InMemoryVectorStore",
]
```

**Step 3: Commit**

```bash
git add packages/core/src/honolulu/memory/
git commit -m "feat: add vector store for long-term memory"
```

---

## Phase 3: Multi-Model Routing

### Task 7: Create OpenAI-Compatible Provider

**Files:**
- Create: `packages/core/src/honolulu/models/openai_provider.py`

**Step 1: Create OpenAI provider**

Create `packages/core/src/honolulu/models/openai_provider.py`:

```python
"""OpenAI-compatible model provider."""

import json
from typing import Any, AsyncGenerator

from honolulu.models.base import ModelProvider, ModelResponse, StreamChunk, ToolCall


class OpenAIProvider(ModelProvider):
    """OpenAI-compatible model provider (works with OpenAI, Qwen, etc.)."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install honolulu[routing]"
            )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    def _convert_tools(self, tools: list[dict] | None) -> list[dict] | None:
        """Convert Anthropic tool format to OpenAI format."""
        if not tools:
            return None

        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                },
            })
        return openai_tools

    def _convert_messages(self, messages: list[dict], system: str | None) -> list[dict]:
        """Convert Anthropic message format to OpenAI format."""
        openai_messages = []

        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                openai_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle tool results
                for block in content:
                    if block.get("type") == "tool_result":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": str(block.get("content", "")),
                        })
                    elif block.get("type") == "text":
                        openai_messages.append({"role": role, "content": block["text"]})

        return openai_messages

    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> ModelResponse:
        """Make a non-streaming call."""
        openai_messages = self._convert_messages(messages, system)
        openai_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        response = await self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                ))

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Make a streaming call."""
        openai_messages = self._convert_messages(messages, system)
        openai_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        current_tool_call: dict[str, Any] | None = None

        async for chunk in await self.client.chat.completions.create(**kwargs):
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            if delta.content:
                yield StreamChunk(type="text", content=delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.function.name:
                        # New tool call starting
                        current_tool_call = {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments_json": tc.function.arguments or "",
                        }
                        yield StreamChunk(
                            type="tool_use_start",
                            tool_call=ToolCall(
                                id=tc.id,
                                name=tc.function.name,
                                arguments={},
                            ),
                        )
                    elif tc.function.arguments and current_tool_call:
                        current_tool_call["arguments_json"] += tc.function.arguments
                        yield StreamChunk(
                            type="tool_use_delta",
                            content=tc.function.arguments,
                        )

            if chunk.choices[0].finish_reason and current_tool_call:
                try:
                    arguments = json.loads(current_tool_call["arguments_json"])
                except json.JSONDecodeError:
                    arguments = {}

                yield StreamChunk(
                    type="tool_use_end",
                    tool_call=ToolCall(
                        id=current_tool_call["id"],
                        name=current_tool_call["name"],
                        arguments=arguments,
                    ),
                )
                current_tool_call = None
```

**Step 2: Commit**

```bash
git add packages/core/src/honolulu/models/openai_provider.py
git commit -m "feat: add OpenAI-compatible model provider"
```

---

### Task 8: Create Model Router

**Files:**
- Create: `packages/core/src/honolulu/models/router.py`

**Step 1: Create router module**

Create `packages/core/src/honolulu/models/router.py`:

```python
"""Multi-model router for Honolulu."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

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
            return self._providers[self._default_provider]

        else:  # SMART or default
            # Use default provider
            return self._providers[self._default_provider]

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
    ):
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
```

**Step 2: Commit**

```bash
git add packages/core/src/honolulu/models/router.py
git commit -m "feat: add multi-model router"
```

---

### Task 9: Update Models Module Exports

**Files:**
- Modify: `packages/core/src/honolulu/models/__init__.py`

**Step 1: Update exports**

Update `packages/core/src/honolulu/models/__init__.py`:

```python
"""Model providers for Honolulu agent."""

from honolulu.models.base import ModelProvider, ModelResponse, ToolCall, StreamChunk
from honolulu.models.claude import ClaudeProvider
from honolulu.models.openai_provider import OpenAIProvider
from honolulu.models.router import ModelRouter, RoutingStrategy, ProviderConfig

__all__ = [
    "ModelProvider",
    "ModelResponse",
    "ToolCall",
    "StreamChunk",
    "ClaudeProvider",
    "OpenAIProvider",
    "ModelRouter",
    "RoutingStrategy",
    "ProviderConfig",
]
```

**Step 2: Commit**

```bash
git add packages/core/src/honolulu/models/__init__.py
git commit -m "feat: export OpenAI provider and router from models module"
```

---

## Phase 4: Integration

### Task 10: Update Config for New Features

**Files:**
- Modify: `packages/core/src/honolulu/config.py`

**Step 1: Add memory and routing config**

Add to `packages/core/src/honolulu/config.py`:

```python
@dataclass
class MemoryConfig:
    """Memory system configuration."""

    enabled: bool = True
    short_term_limit: int = 50
    vector_store: str = "in_memory"  # "chroma" | "in_memory"
    persist_directory: str | None = None


@dataclass
class Config:
    """Main configuration."""

    agent_name: str = "honolulu"
    model: ModelConfig = field(default_factory=ModelConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    permissions: PermissionConfig = field(default_factory=PermissionConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)
```

And update `from_dict` to parse memory config.

**Step 2: Commit**

```bash
git add packages/core/src/honolulu/config.py
git commit -m "feat: add memory configuration to config"
```

---

### Task 11: Final Integration Test

**Step 1: Install dependencies**

```bash
cd packages/core
pip install -e ".[dev,mcp,memory,routing]"
```

**Step 2: Run server and verify**

```bash
./start.sh server
```

**Step 3: Commit all changes**

```bash
git add .
git commit -m "feat: complete MCP, memory, and routing integration"
```

---

## Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: MCP | Tasks 1-4 | Create mcp.py, integrate into server |
| Phase 2: Memory | Tasks 5-6 | Create memory system with vector store |
| Phase 3: Routing | Tasks 7-9 | Create OpenAI provider and router |
| Phase 4: Integration | Tasks 10-11 | Update config, final testing |

**Total Tasks:** 11
**Estimated Time:** 30-45 minutes

---
