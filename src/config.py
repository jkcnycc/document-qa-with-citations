"""Typed configuration. Secrets are referenced by env var name, never inlined."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

log = logging.getLogger(__name__)

# Secrets live in `.env` at the repo root, which is gitignored. Load it once
# here, because this is the module that reads the key - anything that can ask
# for `api_key` has necessarily imported this first.
#
# `override=False` is deliberate: a variable already exported in the shell
# wins over the file. That is the usual convention, and it means a temporary
# `DEEPSEEK_API_KEY=... python ask.py` still works. It also has a sharp edge -
# a stale variable left over in some shell silently beats an edited `.env` -
# so `api_key_source()` below exists to say which one actually supplied it.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file() -> bool:
    """Load `.env` if present. Missing file is normal, not an error."""
    if not ENV_FILE.exists():
        log.debug("no .env at %s - using the process environment only", ENV_FILE)
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        log.warning("python-dotenv is not installed, so %s was not read. "
                    "Run: pip install python-dotenv", ENV_FILE)
        return False
    loaded = load_dotenv(ENV_FILE, override=False)
    log.debug("read %s (%s)", ENV_FILE,
              "values applied" if loaded else "nothing new to apply")
    return loaded


_ENV_FILE_LOADED = _load_env_file()


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

    @property
    def api_key_source(self) -> str:
        """Where the key came from, for error messages and logs.

        Never returns the key itself. The point is the case where an old
        exported variable quietly overrides an edited `.env` - without this
        the symptom is "I changed the file and nothing happened".
        """
        if not self.api_key:
            return "nowhere - it is not set"
        if not ENV_FILE.exists():
            return "the process environment"
        # dotenv did not override, so if the file names it and a value is
        # present, the file is the source only when the shell did not set it.
        from_file = ENV_FILE.read_text(encoding="utf-8", errors="replace")
        named_in_file = any(
            line.strip().removeprefix("export ").startswith(self.api_key_env + "=")
            for line in from_file.splitlines())
        if not named_in_file:
            return "the process environment"
        return (f"{ENV_FILE.name} (or the environment, which would win - "
                f"unset {self.api_key_env} in your shell if edits to "
                f"{ENV_FILE.name} appear to do nothing)")


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
