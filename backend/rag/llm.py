import os
from typing import List

import httpx

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-3-27b-it:free"

SYSTEM_PROMPT = """You are a knowledgeable assistant specializing in insurance documents.
Answer questions accurately and concisely using ONLY the provided context.
If the answer is not in the context, say "I couldn't find that information in the uploaded documents."
Always cite the source document when referencing specific information.
"""


def build_context(chunks: List[dict]) -> str:
    if not chunks:
        return "No relevant documents found."
    parts = [
        f"[Source {i}: {c['source']} | chunk {c['chunk_index']}]\n{c['text']}" for i, c in enumerate(chunks, 1)
    ]
    return "\n\n---\n\n".join(parts)


async def complete(messages: List[dict], *, temperature: float = 0.2, max_tokens: int = 1024) -> dict:
    """Low-level OpenRouter chat completion. Returns the raw JSON payload."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in environment")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("APP_URL", "http://localhost:5173"),
        "X-Title": "Insurance RAG App",
    }
    payload = {
        "model": os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


async def ask_llm(query: str, chunks: List[dict]) -> dict:
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context from uploaded documents:\n\n{context}\n\n---\n\nQuestion: {query}"},
    ]
    data = await complete(messages)
    return {
        "answer": data["choices"][0]["message"]["content"].strip(),
        "sources": sorted({c["source"] for c in chunks}),
        "model": data.get("model", os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)),
        "chunks_used": len(chunks),
    }
