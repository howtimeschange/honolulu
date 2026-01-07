"""Vector store implementations for long-term memory."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from honolulu.memory.base import Memory, MemoryType


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def add(self, memory: Memory) -> None:
        """Add a memory to the store."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """Search for similar memories."""
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all memories."""
        pass


class ChromaVectorStore(VectorStore):
    """ChromaDB-based vector store."""

    def __init__(
        self,
        collection_name: str = "honolulu_memory",
        persist_directory: str | Path | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self._client = None
        self._collection = None
        self._embedding_function = None

    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB client is initialized."""
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            raise ImportError(
                "chromadb is not installed. Install it with: pip install chromadb"
            )

        # Create client
        if self.persist_directory:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory)
            )
        else:
            self._client = chromadb.Client()

        # Create embedding function
        self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model
        )

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    async def add(self, memory: Memory) -> None:
        """Add a memory to ChromaDB."""
        self._ensure_initialized()

        self._collection.add(
            ids=[memory.id],
            documents=[memory.content],
            metadatas=[{
                "memory_type": memory.memory_type.value,
                "created_at": memory.created_at.isoformat(),
                **{k: str(v) for k, v in memory.metadata.items()},
            }],
        )

    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """Search for similar memories in ChromaDB."""
        self._ensure_initialized()

        # Build where clause
        where = None
        if filter_dict:
            where = filter_dict

        results = self._collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
        )

        memories = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results["documents"] else ""
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results.get("distances") else 0

                # Convert distance to relevance score (cosine similarity)
                relevance = 1 - distance

                memory = Memory(
                    id=doc_id,
                    content=doc,
                    memory_type=MemoryType(metadata.get("memory_type", "knowledge")),
                    metadata={
                        k: v for k, v in metadata.items()
                        if k not in ("memory_type", "created_at")
                    },
                    relevance_score=relevance,
                )
                memories.append(memory)

        return memories

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory from ChromaDB."""
        self._ensure_initialized()

        try:
            self._collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False

    async def clear(self) -> None:
        """Clear all memories from the collection."""
        self._ensure_initialized()

        # Delete and recreate collection
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    async def count(self) -> int:
        """Get the number of memories in the store."""
        self._ensure_initialized()
        return self._collection.count()


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store for testing."""

    def __init__(self):
        self._memories: dict[str, Memory] = {}

    async def add(self, memory: Memory) -> None:
        """Add a memory."""
        self._memories[memory.id] = memory

    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """Search memories (simple keyword matching)."""
        query_lower = query.lower()
        results = []

        for memory in self._memories.values():
            # Simple keyword matching
            if query_lower in memory.content.lower():
                # Apply filter
                if filter_dict:
                    memory_type_filter = filter_dict.get("memory_type", {}).get("$in")
                    if memory_type_filter and memory.memory_type.value not in memory_type_filter:
                        continue

                memory.relevance_score = 0.5  # Placeholder score
                results.append(memory)

        return results[:limit]

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    async def clear(self) -> None:
        """Clear all memories."""
        self._memories = {}

    async def count(self) -> int:
        """Get the number of memories."""
        return len(self._memories)
