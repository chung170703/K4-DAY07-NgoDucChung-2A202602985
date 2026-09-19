from __future__ import annotations

from typing import Any, Callable

from .chunking import compute_similarity
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    An in-memory vector store for text chunks.

    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._store: list[dict[str, Any]] = []

    def _make_record(self, doc: Document) -> dict[str, Any]:
        """Build a normalized stored record for one document."""
        metadata = dict(doc.metadata)
        metadata.setdefault("doc_id", doc.id)
        embedding = self._embedding_fn(doc.content)
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": embedding,
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """Run in-memory similarity search over the provided records."""
        query_embedding = self._embedding_fn(query)

        scored = []
        for record in records:
            score = compute_similarity(query_embedding, record["embedding"])
            scored.append((score, record))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        results: list[dict[str, Any]] = []
        for score, record in scored[:top_k]:
            results.append(
                {
                    "id": record["id"],
                    "doc_id": record["metadata"].get("doc_id", record["id"]),
                    "content": record["content"],
                    "metadata": record["metadata"],
                    "score": score,
                }
            )
        return results

    def add_documents(self, docs: list[Document]) -> None:
        """Embed each document's content and store it."""
        for doc in docs:
            self._store.append(self._make_record(doc))

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Find the top_k most similar documents to query."""
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if metadata_filter:
            candidates = [
                record
                for record in self._store
                if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
            ]
        else:
            candidates = self._store

        return self._search_records(query, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        original_size = len(self._store)
        self._store = [record for record in self._store if record["metadata"].get("doc_id") != doc_id]
        return len(self._store) < original_size
