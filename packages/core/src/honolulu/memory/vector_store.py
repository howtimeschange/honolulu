"""Vector store for long-term memory."""

from datetime import datetime
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
        self._client: Any = None
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
                **{k: str(v) for k, v in memory.metadata.items()},
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
                mem_type = metadata.get("type", "knowledge")
                try:
                    memory_type = MemoryType(mem_type)
                except ValueError:
                    memory_type = MemoryType.KNOWLEDGE

                timestamp_str = metadata.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()

                memories.append(Memory(
                    content=doc,
                    memory_type=memory_type,
                    timestamp=timestamp,
                    metadata={k: v for k, v in metadata.items() if k not in ("type", "timestamp")},
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
