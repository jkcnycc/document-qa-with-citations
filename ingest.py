"""Build the search index from the documents folder.

    python ingest.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter

from src.chunker import chunk_sections
from src.config import load_config
from src.index import save_index
from src.loaders import load_sections


def main() -> int:
    parser = argparse.ArgumentParser(description="Index documents for question answering.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-7s %(message)s",
    )

    config = load_config(args.config)

    sections = load_sections(config.documents.path, config.documents.extensions)
    chunks = chunk_sections(
        sections,
        max_chars=config.chunking.max_chars,
        overlap_chars=config.chunking.overlap_chars,
    )
    path = save_index(config.index.path, chunks)

    per_source = Counter(chunk.source for chunk in chunks)
    longest = max((len(chunk.text) for chunk in chunks), default=0)

    print()
    print(f"Indexed {len(chunks)} chunks from {len(per_source)} document(s) -> {path}")
    for source, count in sorted(per_source.items()):
        print(f"    {count:3d}  {source}")
    print(f"    longest chunk: {longest} chars (limit {config.chunking.max_chars})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
