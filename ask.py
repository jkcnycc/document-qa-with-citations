"""Ask a question against the indexed documents.

    python ask.py "How long do I have to request a refund?"
    python ask.py "Do you support Kubernetes?" --show-passages
    python ask.py "..." --provider stub          # no API key needed
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys

from src.answer import answer_question
from src.config import load_config
from src.index import load_index
from src.llm import LLMError, build_llm
from src.retriever import BM25Retriever


def _print_answer(answer, show_passages: bool) -> None:
    print()
    print(f"Q: {answer.question}")
    print()

    if answer.refused:
        print(f"REFUSED - {answer.refusal_reason}")
        print(answer.text)
        if not answer.llm_called:
            print()
            print("No LLM call was made - the question was rejected at retrieval.")
    else:
        print(f"ANSWER  ({answer.provider})")
        print(answer.text)
        print()
        print("SOURCES")
        for number, chunk in enumerate(answer.citations, start=1):
            print(f"  [{number}] {chunk.citation}")

    print()
    print(f"RETRIEVED ({len(answer.retrieved)} passages)")
    for scored in answer.retrieved:
        print(f"  {scored.score:6.2f}  {scored.chunk.citation}")

    if show_passages:
        print()
        print("PASSAGE TEXT")
        for number, scored in enumerate(answer.retrieved, start=1):
            print(f"  --- [{number}] {scored.chunk.citation} ---")
            for line in scored.chunk.text.splitlines():
                print(f"      {line}")
            print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask a question about the indexed documents.")
    parser.add_argument("question", help="the question to answer")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--provider",
        choices=["openai_compatible", "stub"],
        help="override llm.provider from config",
    )
    parser.add_argument("--show-passages", action="store_true", help="print retrieved text")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)-7s %(message)s",
    )

    config = load_config(args.config)
    if args.provider:
        config = dataclasses.replace(
            config, llm=dataclasses.replace(config.llm, provider=args.provider)
        )

    chunks = load_index(config.index.path)
    retriever = BM25Retriever(chunks)

    try:
        llm = build_llm(config.llm)
        answer = answer_question(args.question, retriever, llm, config.retrieval)
    except LLMError as exc:
        print(f"\nLLM error: {exc}", file=sys.stderr)
        return 1

    _print_answer(answer, show_passages=args.show_passages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
