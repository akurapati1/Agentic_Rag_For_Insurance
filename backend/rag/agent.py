"""Agentic RAG pipeline: plan -> retrieve (multi-query) -> grade -> answer.

1. **Plan**   The LLM rewrites the user question into up to N focused search queries
              (decomposes multi-part questions, expands insurance jargon). Falls back to the original
              question if planning fails, so the pipeline degrades gracefully.
2. **Retrieve** Each query is searched; results are merged and de-duplicated by best similarity.
3. **Grade**  Chunks below a similarity floor are dropped, so the model never sees irrelevant context.
4. **Answer** The grounded answer is generated with citations. A `trace` documents each step.
"""
import json
import logging
import re
from typing import Awaitable, Callable, List

from . import llm
from .retrieval import retrieve_chunks

log = logging.getLogger(__name__)

MAX_QUERIES = 3
MIN_SIMILARITY = 0.15

PLANNER_PROMPT = (
    "You rewrite questions about insurance documents into search queries for a vector database. "
    f"Return ONLY a JSON array of 1 to {MAX_QUERIES} short, self-contained search queries that together cover the question. "
    "Use one query for simple questions; split compound questions."
)

Retriever = Callable[[str, int], List[dict]]


def parse_queries(raw: str, original: str) -> List[str]:
    """Extract a JSON list of queries from model output; fall back to [original] on anything unexpected."""
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group(0))
            queries = [q.strip() for q in items if isinstance(q, str) and q.strip()]
            if queries:
                return queries[:MAX_QUERIES]
        except (json.JSONDecodeError, TypeError):
            pass
    return [original]


def merge_chunks(results: List[List[dict]], limit: int) -> List[dict]:
    """Merge per-query results, keeping each chunk's best similarity, sorted descending."""
    best: dict[tuple, dict] = {}
    for chunks in results:
        for c in chunks:
            key = (c["source"], c["chunk_index"])
            if key not in best or c["similarity"] > best[key]["similarity"]:
                best[key] = c
    return sorted(best.values(), key=lambda c: c["similarity"], reverse=True)[:limit]


async def plan_queries(question: str) -> List[str]:
    try:
        data = await llm.complete(
            [{"role": "system", "content": PLANNER_PROMPT}, {"role": "user", "content": question}],
            temperature=0.0,
            max_tokens=200,
        )
        return parse_queries(data["choices"][0]["message"]["content"], question)
    except Exception as exc:  # planning is best-effort
        log.warning("Query planning failed, using original question: %s", exc)
        return [question]


async def run_agent(
    question: str,
    top_k: int = 6,
    *,
    retriever: Retriever = retrieve_chunks,
    answerer: Callable[[str, List[dict]], Awaitable[dict]] = llm.ask_llm,
    planner: Callable[[str], Awaitable[List[str]]] = plan_queries,
) -> dict:
    queries = await planner(question)
    retrieved = [retriever(q, top_k) for q in queries]
    candidates = merge_chunks(retrieved, limit=top_k)
    relevant = [c for c in candidates if c["similarity"] >= MIN_SIMILARITY]

    trace = {
        "queries": queries,
        "retrieved": len(candidates),
        "kept_after_grading": len(relevant),
    }
    if not candidates:
        return {"answer": "No documents have been uploaded yet. Please upload some PDF files first.",
                "sources": [], "model": "none", "chunks_used": 0, "trace": trace}
    if not relevant:
        return {"answer": "I couldn't find that information in the uploaded documents.",
                "sources": [], "model": "none", "chunks_used": 0, "trace": trace}

    result = await answerer(question, relevant)
    result["trace"] = trace
    return result
