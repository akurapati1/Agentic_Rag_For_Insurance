from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_validation():
    assert client.post("/api/chat", json={"query": "", "top_k": 3}).status_code == 422
    assert client.post("/api/chat", json={"query": "x", "top_k": 0}).status_code == 422


def test_chat_success(monkeypatch):
    async def fake(q, top_k):
        return {"answer": "42", "sources": ["p.pdf"], "model": "m", "chunks_used": 1, "trace": {"queries": [q]}}

    monkeypatch.setattr(main, "run_agent", fake)
    body = client.post("/api/chat", json={"query": "hi"}).json()
    assert body["answer"] == "42" and body["trace"]["queries"] == ["hi"]


def test_chat_missing_key_is_500(monkeypatch):
    async def boom(q, top_k):
        raise ValueError("OPENROUTER_API_KEY not set in environment")

    monkeypatch.setattr(main, "run_agent", boom)
    assert client.post("/api/chat", json={"query": "hi"}).status_code == 500


def test_upload_skips_non_pdf_and_delete_404(monkeypatch):
    r = client.post("/api/upload", files={"files": ("notes.txt", b"hello")})
    assert r.json()["results"][0]["status"] == "skipped_not_pdf"
    monkeypatch.setattr(main, "delete_document", lambda f: {"deleted": False})
    assert client.delete("/api/documents/nope.pdf").status_code == 404
