"""RAG tool implementations."""

import asyncio
from typing import Dict, List, Optional

from core.constants import QueryType, ToolStatus
from core.logger import setup_logger
from core.types import ToolMetadata, ToolResult

from ..base import RAGTool

logger = setup_logger(__name__)


class ChromaDBTool(RAGTool):
    """ChromaDB document search tool."""

    def __init__(self, db_path: str = "backend/chroma_data"):
        """Initialize ChromaDB tool."""
        super().__init__()
        self.db_path = db_path
        self._collection = None
        self._embedder = None
        self._init_chromadb()

    def _init_chromadb(self):
        """Initialize ChromaDB connection."""
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            # Use persistent client
            client = chromadb.PersistentClient(path=self.db_path)
            self._collection = client.get_or_create_collection(
                name="documents", metadata={"hnsw:space": "cosine"}
            )
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")

            logger.info(f"ChromaDB initialized with path: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.set_status(ToolStatus.UNAVAILABLE, f"ChromaDB init failed: {e}")

    def _define_metadata(self) -> ToolMetadata:
        """Define tool metadata."""
        return ToolMetadata(
            name="document_rag",
            description="Search user's uploaded documents using RAG",
            required_online=False,
            timeout_seconds=5,
            priority=1,
            supported_query_types=[QueryType.DOCUMENT, QueryType.GENERAL],
            cost_score=0.3,
            latency_score=0.2,
            example_queries=[
                "What did the document say about X?",
                "Find information about topic Y in my files",
                "Search my notes for XYZ",
            ],
        )

    async def execute(
        self, query: str, top_k: int = 3, min_similarity: float = 0.3, **kwargs
    ) -> ToolResult:
        """
        Execute document search using ChromaDB.

        Args:
            query: Search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            **kwargs: Additional parameters

        Returns:
            ToolResult with document matches
        """
        start_time = asyncio.get_event_loop().time()

        if self._collection is None or self._embedder is None:
            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=False,
                error_message="ChromaDB not initialized",
                execution_time_ms=0,
                confidence=0.0,
            )

        try:
            results = await asyncio.to_thread(
                self._search_documents, query, top_k, min_similarity
            )

            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            if not results:
                return ToolResult(
                    tool_name=self.metadata.name,
                    query=query,
                    success=True,
                    data="No matching documents found",
                    execution_time_ms=execution_time,
                    confidence=0.0,
                    metadata={"num_results": 0},
                )

            # Format results
            formatted_results = "\n".join(
                [
                    f"**From {r['source']}** (similarity: {r['similarity']:.2f}):\n{r['content'][:300]}..."
                    for r in results
                ]
            )

            document_ids = [r.get("source", "") for r in results]

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=True,
                data=formatted_results,
                execution_time_ms=execution_time,
                document_ids=document_ids,
                confidence=min(0.9, results[0]["similarity"]) if results else 0.0,
                metadata={"num_results": len(results)},
            )

        except Exception as e:
            logger.error(f"Document search error: {e}")
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                confidence=0.0,
            )

    def _search_documents(
        self, query: str, top_k: int, min_similarity: float
    ) -> List[Dict]:
        """Search documents using ChromaDB (blocking operation)."""
        try:
            # Generate query embedding
            query_embedding = self._embedder.encode(query).tolist()

            # Query ChromaDB
            results = self._collection.query(
                query_embeddings=[query_embedding], n_results=top_k
            )

            # Process results
            documents = []

            if (
                "documents" in results
                and len(results["documents"]) > 0
                and len(results["documents"][0]) > 0
            ):

                for doc, metadata, embedding in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["embeddings"][0],
                ):

                    # Calculate similarity
                    from numpy import dot
                    from numpy.linalg import norm

                    similarity = dot(query_embedding, embedding) / (
                        norm(query_embedding) * norm(embedding)
                    )

                    if similarity >= min_similarity:
                        documents.append(
                            {
                                "content": doc,
                                "source": metadata.get("source", "unknown"),
                                "similarity": float(similarity),
                            }
                        )

            return documents

        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            raise

    async def health_check(self) -> ToolStatus:
        """Check if ChromaDB is accessible."""
        try:
            if self._collection is None:
                self.set_status(ToolStatus.UNAVAILABLE, "ChromaDB not initialized")
                return ToolStatus.UNAVAILABLE

            # Try a simple query
            _ = self._collection.get()  # Get collection count

            self.set_status(ToolStatus.AVAILABLE)
            return ToolStatus.AVAILABLE

        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            self.set_status(ToolStatus.UNAVAILABLE, str(e))
            return ToolStatus.UNAVAILABLE
