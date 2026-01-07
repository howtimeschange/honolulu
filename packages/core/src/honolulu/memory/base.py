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
                # Note: This is sync, but vector_store.add is async
                # In real usage, this should be handled properly
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._vector_store.add(oldest))
                    else:
                        loop.run_until_complete(self._vector_store.add(oldest))
                except RuntimeError:
                    pass  # No event loop, skip long-term storage

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
