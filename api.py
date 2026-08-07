"""HTTP wrapper around the existing question-answering pipeline.

    pip install fastapi uvicorn
    uvicorn api:app --port 8000

Nothing in src/ changes - this only exposes it over HTTP so a browser can call
it. The index and the retriever are built once at startup rather than per
request, because rebuilding BM25 on every question would dominate the latency.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.answer import answer_question
from src.config import load_config
from src.index import load_index
from src.llm import LLMError, build_llm
from src.retriever import BM25Retriever

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
log = logging.getLogger("api")

state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    config = load_config("config.yaml")
    chunks = load_index(config.index.path)
    state["config"] = config
    state["retriever"] = BM25Retriever(chunks)
    state["llm"] = build_llm(config.llm)
    log.info("ready: %d chunks, provider %s", len(chunks), config.llm.provider)
    yield
    state.clear()


app = FastAPI(title="Document Q&A", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class Source(BaseModel):
    # The passage number the model actually cited. The UI must not renumber
    # these from a list index - the answer text refers to these numbers.
    number: int
    citation: str
    text: str


class Passage(BaseModel):
    score: float
    citation: str


class AskResponse(BaseModel):
    question: str
    text: str
    refused: bool
    refusal_reason: str
    llm_called: bool
    provider: str
    sources: List[Source]
    retrieved: List[Passage]


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "provider": state["config"].llm.provider}


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question is empty")

    try:
        answer = answer_question(
            question,
            state["retriever"],
            state["llm"],
            state["config"].retrieval,
        )
    except LLMError as exc:
        # A provider failure is not the caller's fault, and the message is safe
        # to show - build_llm already keeps the key out of it.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AskResponse(
        question=answer.question,
        text=answer.text,
        refused=answer.refused,
        refusal_reason=answer.refusal_reason,
        llm_called=answer.llm_called,
        provider=answer.provider,
        sources=[
            Source(
                # Recover the passage number by finding where this chunk sat in
                # the retrieved list, which is what the model was numbering.
                number=next(
                    index
                    for index, scored in enumerate(answer.retrieved, start=1)
                    if scored.chunk.id == chunk.id
                ),
                citation=chunk.citation,
                text=chunk.text[:400],
            )
            for chunk in answer.citations
        ],
        retrieved=[
            Passage(score=round(scored.score, 2), citation=scored.chunk.citation)
            for scored in answer.retrieved
        ],
    )
