"""BM25 retrieval.

Deliberately not embedding-based: no vector API, no model download, no GPU,
runs offline, and the scores are reproducible - which is what makes the
retrieval layer unit-testable. A vector retriever can be dropped in behind the
same search() signature when a project actually needs semantic matching.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

from .chunker import Chunk

_WORD_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[一-鿿]+")

# Small, deliberate list: aggressive stopword removal hurts short questions.
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "has", "have", "how", "i", "if", "in", "is", "it", "its", "long",
    "me", "my", "of", "on", "or", "that", "the", "their", "there", "this", "to",
    "was", "what", "when", "where", "which", "who", "why", "will", "with", "you",
    "your",
}


def tokenize(text: str) -> List[str]:
    """Lowercase word tokens, plus character bigrams for CJK.

    CJK text has no spaces, so a word regex returns nothing useful. Bigrams are
    a cheap, dependency-free stand-in for a real segmenter and are good enough
    for retrieval.
    """
    lowered = text.lower()
    tokens = [token for token in _WORD_RE.findall(lowered) if token not in _STOPWORDS]

    for run in _CJK_RE.findall(lowered):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[index : index + 2] for index in range(len(run) - 1))

    return tokens


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class BM25Retriever:
    """Standard BM25-Okapi over pre-chunked documents."""

    def __init__(self, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self._chunks = chunks
        self._k1 = k1
        self._b = b

        self._term_frequencies: List[Counter] = [Counter(tokenize(c.text)) for c in chunks]
        self._lengths: List[int] = [sum(tf.values()) for tf in self._term_frequencies]
        self._average_length = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0.0

        document_frequency: Counter = Counter()
        for term_frequency in self._term_frequencies:
            document_frequency.update(term_frequency.keys())

        total = len(chunks)
        self._idf: Dict[str, float] = {
            term: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for term, count in document_frequency.items()
        }

    def __len__(self) -> int:
        return len(self._chunks)

    def score(self, query_tokens: List[str], document_index: int) -> float:
        term_frequency = self._term_frequencies[document_index]
        length = self._lengths[document_index]
        if not length:
            return 0.0

        normaliser = self._k1 * (
            1 - self._b + self._b * length / (self._average_length or 1.0)
        )

        total = 0.0
        for token in query_tokens:
            frequency = term_frequency.get(token, 0)
            if not frequency:
                continue
            total += self._idf.get(token, 0.0) * frequency * (self._k1 + 1) / (frequency + normaliser)
        return total

    def search(self, query: str, top_k: int = 4) -> List[ScoredChunk]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scored = [
            ScoredChunk(chunk=self._chunks[index], score=self.score(query_tokens, index))
            for index in range(len(self._chunks))
        ]
        scored = [item for item in scored if item.score > 0]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]
