from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        if self.store.get_collection_size() == 0:
            return "No documents in knowledge base. Please add documents before asking questions."

        results = self.store.search(question, top_k=top_k)
        if not results:
            return "I couldn't find relevant information in the knowledge base to answer this question."

        context_blocks = []
        for i, result in enumerate(results, start=1):
            metadata = result.get("metadata", {}) or {}
            source = metadata.get("source") or metadata.get("doc_id") or result.get("id", "unknown")
            content = result.get("content", "")
            context_blocks.append(f"[{i}] (source: {source})\n{content}")

        context = "\n\n".join(context_blocks)

        prompt = (
            "You are a helpful assistant answering questions using ONLY the "
            "context provided below. Each context chunk is numbered like [1], "
            "[2], [3]. When you use information from a chunk, cite its bracketed "
            "number(s) in your answer. Do not fabricate information beyond what "
            "is given in the context. If the context does not contain the answer, "
            "explicitly say that you could not find the answer in the provided "
            "context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer (cite chunk numbers like [1]):"
        )

        return self.llm_fn(prompt)
