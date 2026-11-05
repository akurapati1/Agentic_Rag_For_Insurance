import asyncio

from rag.agent import merge_chunks, parse_queries, run_agent


def chunk(src, idx, sim):
    return {"text": "t", "source": src, "chunk_index": idx, "similarity": sim}


def test_parse_queries_valid_and_fallback():
    assert parse_queries('Sure: ["deductible amount", "comprehensive coverage"]', "q") == ["deductible amount", "comprehensive coverage"]
    assert parse_queries("no json here", "orig") == ["orig"]
    assert parse_queries("[1, 2]", "orig") == ["orig"]
    assert len(parse_queries('["a","b","c","d","e"]', "q")) == 3


def test_merge_dedupes_keeping_best_similarity():
    merged = merge_chunks([[chunk("a", 0, 0.4), chunk("b", 1, 0.9)], [chunk("a", 0, 0.7)]], limit=5)
    assert [(c["source"], c["similarity"]) for c in merged] == [("b", 0.9), ("a", 0.7)]


def test_agent_happy_path_and_grading():
    seen = {}

    async def planner(q):
        return ["deductible", "coverage"]

    async def answerer(q, chunks):
        seen["chunks"] = chunks
        return {"answer": "ok", "sources": ["a"], "model": "m", "chunks_used": len(chunks)}

    def retriever(q, k):
        return [chunk("a", 0, 0.8), chunk("noise", 9, 0.01)]

    out = asyncio.run(run_agent("q", retriever=retriever, answerer=answerer, planner=planner))
    assert out["answer"] == "ok" and out["trace"]["queries"] == ["deductible", "coverage"]
    assert [c["source"] for c in seen["chunks"]] == ["a"]  # low-similarity chunk graded out
    assert out["trace"]["kept_after_grading"] == 1


def test_agent_no_documents_and_irrelevant():
    async def planner(q):
        return [q]

    async def answerer(q, c):
        raise AssertionError("must not be called")

    empty = asyncio.run(run_agent("q", retriever=lambda q, k: [], answerer=answerer, planner=planner))
    assert "upload" in empty["answer"].lower()
    irrelevant = asyncio.run(run_agent("q", retriever=lambda q, k: [chunk("a", 0, 0.01)], answerer=answerer, planner=planner))
    assert "couldn't find" in irrelevant["answer"]
