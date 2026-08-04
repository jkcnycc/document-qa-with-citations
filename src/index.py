"""Index persistence.

Only the chunks are stored. BM25 statistics rebuild in milliseconds, and
keeping the on-disk format plain readable JSON means the index can be diffed
and inspected instead of being a binary blob nobody can debug.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .chunker import Chunk

_FORMAT_VERSION = 1


def save_index(path: str | Path, chunks: List[Chunk]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "format_version": _FORMAT_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunk_count": len(chunks),
        "chunks": [asdict(chunk) for chunk in chunks],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_index(path: str | Path) -> List[Chunk]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(
            f"No index at {source}. Build one first with: python ingest.py"
        )

    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("format_version") != _FORMAT_VERSION:
        raise ValueError(
            f"Index at {source} was built by a different version - rebuild with: python ingest.py"
        )

    return [Chunk(**record) for record in payload["chunks"]]
