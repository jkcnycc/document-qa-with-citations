"""Split sections into retrievable chunks.

Chunks break on paragraph boundaries where possible. A sentence cut in half
retrieves badly and reads worse when it ends up quoted in a citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .loaders import Section

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class Chunk:
    id: int
    source: str
    location: str
    text: str

    @property
    def citation(self) -> str:
        return f"{self.source} > {self.location}"


def _split_long_paragraph(paragraph: str, max_chars: int) -> List[str]:
    """Last resort for a paragraph that is itself longer than the limit."""
    pieces: List[str] = []
    remaining = paragraph
    while len(remaining) > max_chars:
        window = remaining[:max_chars]
        # Prefer to break after a sentence, then after a space, then hard.
        cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
        if cut < max_chars // 2:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = max_chars
        else:
            cut += 1
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def chunk_sections(
    sections: List[Section], max_chars: int = 900, overlap_chars: int = 150
) -> List[Chunk]:
    """Pack paragraphs into chunks of at most max_chars, with a little overlap.

    The overlap keeps an answer intact when it happens to straddle a boundary.
    """
    chunks: List[Chunk] = []
    next_id = 0

    for section in sections:
        paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(section.text) if p.strip()]

        buffer = ""
        for paragraph in paragraphs:
            for piece in (
                _split_long_paragraph(paragraph, max_chars)
                if len(paragraph) > max_chars
                else [paragraph]
            ):
                candidate = f"{buffer}\n\n{piece}".strip() if buffer else piece
                if len(candidate) <= max_chars:
                    buffer = candidate
                    continue

                chunks.append(
                    Chunk(id=next_id, source=section.source, location=section.location, text=buffer)
                )
                next_id += 1
                tail = buffer[-overlap_chars:] if overlap_chars else ""
                buffer = f"{tail}\n\n{piece}".strip() if tail else piece

        if buffer:
            chunks.append(
                Chunk(id=next_id, source=section.source, location=section.location, text=buffer)
            )
            next_id += 1

    return chunks
