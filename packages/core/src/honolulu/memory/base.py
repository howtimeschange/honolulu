"""Base classes for the memory system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import hashlib
import json


class MemoryType(str, Enum):
    """Types of memory."""

    CONVERSATION = "conversation"  # Chat messages
    TASK = "task"  # Task execution details
    KNOWLEDGE = "knowledge"  # General knowledge/facts
    TOOL_RESULT = "tool_result"  # Tool execution results
    USER_PREFERENCE = "user_preference"  # User preferences learned


@dataclass
class Memory:
    """A single memory entry."""

    id: str
    content: str
    memory_type: MemoryType
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    relevance_score: float = 0.0  # Set during retrieval

    @classmethod
    def create(
        cls,
        content: str,
        memory_type: MemoryType,
        metadata: dict[str, Any] | None = None,
    ) -> "Memory":
        """Create a new memory with auto-generated ID."""
        # Generate ID from content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        memory_id = f"{memory_type.value}_{timestamp}_{content_hash}"

        return cls(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Memory":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            relevance_score=data.get("relevance_score", 0.0),
        )


class MemoryManager:
    """Manages multi-layer memory system."""

    def __init__(
        self,
        vector_store: "VectorStore | None" = None,
        short_term_limit: int = 50,
        compression_threshold: int = 100000,  # tokens
    ):
        from honolulu.memory.vector_store import VectorStore

        self.vector_store = vector_store
        self.short_term_limit = short_term_limit
        self.compression_threshold = compression_threshold

        # Short-term memory (current conversation)
        self.short_term: list[dict] = []

        # Working memory (task-related context)
        self.working_memory: dict[str, Any] = {}

    async def add_message(self, role: str, content: str) -> None:
        """Add a message to short-term memory."""
        self.short_term.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

        # Trim if exceeds limit
        if len(self.short_term) > self.short_term_limit:
            self.short_term = self.short_term[-self.short_term_limit:]

    async def add_to_long_term(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add content to long-term memory (vector store)."""
        if not self.vector_store:
            return ""

        memory = Memory.create(content, memory_type, metadata)
        await self.vector_store.add(memory)
        return memory.id

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        memory_types: list[MemoryType] | None = None,
    ) -> list[Memory]:
        """Retrieve relevant memories."""
        memories: list[Memory] = []

        # Search long-term memory
        if self.vector_store:
            filter_dict = None
            if memory_types:
                filter_dict = {
                    "memory_type": {"$in": [t.value for t in memory_types]}
                }

            long_term = await self.vector_store.search(
                query,
                limit=limit,
                filter_dict=filter_dict,
            )
            memories.extend(long_term)

        return memories

    async def build_context(
        self,
        query: str,
        max_tokens: int = 50000,
    ) -> list[dict]:
        """Build context for model call with relevant memories."""
        context_parts = []

        # 1. Retrieve relevant long-term memories
        relevant_memories = await self.retrieve(query, limit=5)

        if relevant_memories:
            memory_text = "\n".join([
                f"[{m.memory_type.value}] {m.content}"
                for m in relevant_memories
            ])
            context_parts.append({
                "role": "system",
                "content": f"Relevant context from memory:\n{memory_text}",
            })

        # 2. Add recent conversation history
        context_parts.extend(self.short_term)

        # 3. Compress if needed
        total_chars = sum(len(str(p.get("content", ""))) for p in context_parts)
        estimated_tokens = total_chars // 4

        if estimated_tokens > max_tokens:
            context_parts = await self._compress_context(context_parts, max_tokens)

        return context_parts

    async def _compress_context(
        self,
        context: list[dict],
        max_tokens: int,
    ) -> list[dict]:
        """Compress context to fit within token limit."""
        # Simple strategy: keep system messages and recent conversation
        system_msgs = [m for m in context if m.get("role") == "system"]
        conv_msgs = [m for m in context if m.get("role") != "system"]

        # Keep last N conversation messages
        keep_count = min(len(conv_msgs), 20)
        recent_conv = conv_msgs[-keep_count:]

        return system_msgs + recent_conv

    def set_working_context(self, key: str, value: Any) -> None:
        """Set working memory context."""
        self.working_memory[key] = value

    def get_working_context(self, key: str) -> Any:
        """Get working memory context."""
        return self.working_memory.get(key)

    def clear_working_memory(self) -> None:
        """Clear working memory."""
        self.working_memory = {}

    def clear_short_term(self) -> None:
        """Clear short-term memory."""
        self.short_term = []

    async def save_conversation_summary(self, summary: str) -> None:
        """Save a conversation summary to long-term memory."""
        await self.add_to_long_term(
            summary,
            MemoryType.CONVERSATION,
            {"type": "summary"},
        )

    async def save_task_result(
        self,
        task: str,
        result: str,
        success: bool,
    ) -> None:
        """Save task execution result to long-term memory."""
        await self.add_to_long_term(
            f"Task: {task}\nResult: {result}",
            MemoryType.TASK,
            {"success": success},
        )

    async def learn_user_preference(
        self,
        preference: str,
        context: str | None = None,
    ) -> None:
        """Learn and store a user preference."""
        content = preference
        if context:
            content = f"{preference} (Context: {context})"

        await self.add_to_long_term(
            content,
            MemoryType.USER_PREFERENCE,
        )


# Import VectorStore for type hints
from honolulu.memory.vector_store import VectorStore
