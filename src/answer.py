"""Answering, with the guardrails that actually matter.

Three independent gates stand between a question and an answer. Any one of them
can refuse. The point is that a wrong answer with a confident tone is worse for
a client than no answer at all.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .chunker import Chunk
from .config import RetrievalConfig
from .llm import LLMClient
from .retriever import BM25Retriever, ScoredChunk

log = logging.getLogger(__name__)

REFUSAL_TEXT = "I could not find an answer to this in the provided documents."

SYSTEM_PROMPT = """You are a document question-answering assistant.

Rules, in priority order:
1. Answer ONLY from the numbered context passages below. Never use outside
   knowledge, even if you are confident it is correct.
2. Cite the passage number in square brackets after each claim, like [1] or
   [2][3]. Every factual statement needs a citation.
3. If the passages do not contain enough information to answer the question,
   reply with exactly:
   NOT_FOUND
   Do not guess, do not fill gaps, and do not offer general advice.
4. Be concise. Two to four sentences is usually enough."""

_CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass
class Answer:
    question: str
    text: str
    refused: bool
    refusal_reason: str = ""
    citations: List[Chunk] = field(default_factory=list)
    retrieved: List[ScoredChunk] = field(default_factory=list)
    provider: str = ""
    llm_called: bool = False


def build_user_prompt(question: str, passages: List[ScoredChunk]) -> str:
    blocks = [f"Question: {question}", "", "Context passages:", ""]
    for number, scored in enumerate(passages, start=1):
        blocks.append(f"[{number}] {scored.chunk.citation}")
        blocks.append(scored.chunk.text)
        blocks.append("")
    return "\n".join(blocks).strip()


def extract_citations(text: str, passage_count: int) -> List[int]:
    """Return the valid, de-duplicated passage numbers referenced in an answer."""
    seen: List[int] = []
    for raw in _CITATION_RE.findall(text):
        number = int(raw)
        if 1 <= number <= passage_count and number not in seen:
            seen.append(number)
    return seen


def answer_question(
    question: str,
    retriever: BM25Retriever,
    llm: LLMClient,
    config: RetrievalConfig,
) -> Answer:
    provider = getattr(llm, "name", type(llm).__name__)
    retrieved = retriever.search(question, top_k=config.top_k)

    # Gate 1 - relevance. If nothing in the corpus is close enough, refuse
    # without calling the model at all. The cheapest hallucination to prevent
    # is the one you never pay for.
    best_score = retrieved[0].score if retrieved else 0.0
    if best_score < config.min_score:
        log.info(
            "refusing before LLM call: best score %.2f < min_score %.2f",
            best_score,
            config.min_score,
        )
        return Answer(
            question=question,
            text=REFUSAL_TEXT,
            refused=True,
            refusal_reason=(
                f"no passage scored above the relevance threshold "
                f"(best {best_score:.2f} < {config.min_score:.2f})"
            ),
            retrieved=retrieved,
            provider=provider,
            llm_called=False,
        )

    raw = llm.complete(SYSTEM_PROMPT, build_user_prompt(question, retrieved))

    # Gate 2 - the model itself reporting insufficient context.
    if raw.strip().upper().startswith("NOT_FOUND"):
        return Answer(
            question=question,
            text=REFUSAL_TEXT,
            refused=True,
            refusal_reason="the model reported that the passages do not answer the question",
            retrieved=retrieved,
            provider=provider,
            llm_called=True,
        )

    # Gate 3 - an uncited answer is indistinguishable from an invented one, so
    # it is treated as one.
    numbers = extract_citations(raw, passage_count=len(retrieved))
    if not numbers:
        log.warning("answer contained no valid citations - refusing")
        return Answer(
            question=question,
            text=REFUSAL_TEXT,
            refused=True,
            refusal_reason="the answer cited no source passage, so it could not be verified",
            retrieved=retrieved,
            provider=provider,
            llm_called=True,
        )

    return Answer(
        question=question,
        text=raw,
        refused=False,
        citations=[retrieved[number - 1].chunk for number in numbers],
        retrieved=retrieved,
        provider=provider,
        llm_called=True,
    )
