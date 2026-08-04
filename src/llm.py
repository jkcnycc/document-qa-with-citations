"""LLM access.

Everything goes through a plain OpenAI-compatible chat endpoint, so DeepSeek,
OpenAI, or any compatible gateway is a base_url and model change in config -
no vendor lock-in, and no code to rewrite when a client switches provider.
"""

from __future__ import annotations

import logging
import re
from typing import List, Protocol

from .config import LLMConfig

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    name: str

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class OpenAICompatibleClient:
    """Works against DeepSeek, OpenAI, or any OpenAI-compatible endpoint."""

    def __init__(self, config: LLMConfig) -> None:
        if not config.api_key:
            raise LLMError(
                f"No API key found in environment variable {config.api_key_env}. "
                'Set it, or run with provider "stub" to try the pipeline offline.'
            )
        self._config = config
        self.name = f"{config.model} @ {config.base_url}"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise LLMError("The openai package is required: pip install openai") from exc

        config = self._config
        client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - surface provider errors uniformly
            raise LLMError(f"{config.model} request failed: {exc}") from exc

        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise LLMError(f"{config.model} returned an empty response")
        return content


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class StubClient:
    """Offline stand-in so the pipeline runs with no API key.

    Retrieval, both refusal gates and the citation check are all real - only the
    natural-language generation is faked. Because a stub has no semantic
    judgement, "does the passage actually address the question" is approximated
    by checking whether the question's most distinctive word appears in it. A
    real model does this properly; the heuristic exists so the NOT_FOUND path is
    still demonstrable offline.
    """

    name = "stub (offline, no API key)"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        question = self._extract_question(user_prompt)
        passages = self._extract_passages(user_prompt)
        if not passages:
            return "NOT_FOUND"

        if not self._passage_addresses_question(question, passages[0]):
            return "NOT_FOUND"

        sentences = [s.strip() for s in _SENTENCE_RE.split(passages[0]) if s.strip()]
        excerpt = " ".join(sentences[:2]) if sentences else passages[0][:280]
        return f"[stub answer] {excerpt} [1]"

    @staticmethod
    def _extract_question(user_prompt: str) -> str:
        match = re.search(r"^Question:\s*(.+)$", user_prompt, flags=re.MULTILINE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_passages(user_prompt: str) -> List[str]:
        blocks = re.split(r"^\[(\d+)\]\s.*$", user_prompt, flags=re.MULTILINE)
        # re.split with one group yields [before, id, body, id, body, ...]
        return [block.strip() for block in blocks[2::2] if block.strip()]

    @staticmethod
    def _passage_addresses_question(question: str, passage: str) -> bool:
        from .retriever import tokenize

        tokens = [token for token in tokenize(question) if len(token) > 3]
        if not tokens:
            return True

        # Longest token is a crude proxy for "most specific term in the question".
        key_term = max(tokens, key=len)
        return key_term in passage.lower()


def build_llm(config: LLMConfig) -> LLMClient:
    if config.provider == "stub":
        return StubClient()
    if config.provider == "openai_compatible":
        return OpenAICompatibleClient(config)
    raise LLMError(f"Unknown llm.provider {config.provider!r} (expected 'openai_compatible' or 'stub')")
