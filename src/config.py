"""Typed configuration. Secrets are referenced by env var name, never inlined."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml


@dataclass(frozen=True)
class DocumentsConfig:
    path: str = "docs"
    extensions: Tuple[str, ...] = (".md", ".txt", ".pdf")


@dataclass(frozen=True)
class ChunkingConfig:
    max_chars: int = 900
    overlap_chars: int = 150


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 4
    min_score: float = 3.0


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "openai_compatible"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    api_key_env: str = "DEEPSEEK_API_KEY"
    temperature: float = 0.0
    max_tokens: int = 700
    timeout_seconds: float = 60.0

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


@dataclass(frozen=True)
class IndexConfig:
    path: str = ".index/index.json"


@dataclass(frozen=True)
class Config:
    documents: DocumentsConfig = field(default_factory=DocumentsConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    index: IndexConfig = field(default_factory=IndexConfig)


def load_config(path: str | Path) -> Config:
    raw: Dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    documents_raw = dict(raw.get("documents", {}))
    if "extensions" in documents_raw:
        documents_raw["extensions"] = tuple(documents_raw["extensions"])

    return Config(
        documents=DocumentsConfig(**documents_raw),
        chunking=ChunkingConfig(**raw.get("chunking", {})),
        retrieval=RetrievalConfig(**raw.get("retrieval", {})),
        llm=LLMConfig(**raw.get("llm", {})),
        index=IndexConfig(**raw.get("index", {})),
    )
