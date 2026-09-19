from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Split AFTER the sentence-ending punctuation (lookbehind) so the
        # delimiter stays attached to the preceding sentence instead of
        # being devoured by the split. \s+ also covers the ".\n" case
        # since a newline is whitespace.
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", text.strip())
            if s.strip()
        ]

        if not sentences:
            return []

        chunks: list[str] = []
        for start in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[start : start + self.max_sentences_per_chunk]
            chunks.append(" ".join(group).strip())

        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        # Base case (a): already fits.
        if len(current_text) <= self.chunk_size:
            return [current_text]

        # Base case (b): no separators left — hard character-slice fallback.
        if not remaining_separators:
            return [
                current_text[i : i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]
        rest_separators = remaining_separators[1:]

        # If this separator doesn't occur here, try the next one.
        if separator == "" or separator not in current_text:
            if separator == "":
                # "" means slice by chunk_size directly (last resort separator).
                return [
                    current_text[i : i + self.chunk_size]
                    for i in range(0, len(current_text), self.chunk_size)
                ]
            return self._split(current_text, rest_separators)

        pieces = current_text.split(separator)

        # Recurse into any piece that is still too large on its own.
        split_pieces: list[str] = []
        for piece in pieces:
            if len(piece) > self.chunk_size:
                split_pieces.extend(self._split(piece, rest_separators))
            else:
                split_pieces.append(piece)

        # Merge adjacent small pieces back together (rejoining with the
        # separator that was used to split) up to just under chunk_size,
        # instead of emitting each tiny piece as its own chunk.
        merged: list[str] = []
        current = ""
        for piece in split_pieces:
            if not piece:
                continue
            if not current:
                candidate = piece
            else:
                candidate = current + separator + piece
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    merged.append(current)
                current = piece
        if current:
            merged.append(current)

        return merged if merged else [current_text]


class HeadingChunker:
    """
    Split text by Markdown headings (#, ##, ###) or regulation articles (Điều X:).

    For sections exceeding max_chunk_size, recursively sub-splits and injects
    the parent heading context into each sub-chunk to preserve provenance.
    """

    def __init__(self, max_chunk_size: int = 500) -> None:
        self.max_chunk_size = max_chunk_size
        self._recursive_chunker = RecursiveChunker(chunk_size=max_chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        heading_pattern = r"(?=(?:^|\n)#{1,6}\s+|(?:^|\n)Điều\s+\d+[:\.])"
        sections = [s.strip() for s in re.split(heading_pattern, text.strip()) if s.strip()]

        if not sections:
            return []

        chunks: list[str] = []
        for section in sections:
            if len(section) <= self.max_chunk_size:
                chunks.append(section)
            else:
                first_line, _, rest = section.partition("\n")
                heading_title = first_line.strip() if first_line.startswith(("#", "Điều")) else ""

                sub_text = rest.strip() if heading_title else section
                sub_chunks = self._recursive_chunker.chunk(sub_text)

                for sc in sub_chunks:
                    if heading_title and not sc.startswith(heading_title):
                        chunks.append(f"{heading_title}\n{sc}")
                    else:
                        chunks.append(sc)

        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size),
            "by_sentences": SentenceChunker(),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        result: dict = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = (sum(len(c) for c in chunks) / count) if count else 0.0
            result[name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }
        return result
