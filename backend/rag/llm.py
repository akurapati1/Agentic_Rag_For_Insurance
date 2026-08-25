import os
from typing import List
import httpx

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Free models on OpenRouter — change to any free model you prefer
DEFAULT_MODEL = "google/gemma-3-27b-it:free"

SYSTEM_PROMPT = """You are a knowledgeable assistant specializing in insurance documents.
Answer questions accurately and concisely using ONLY the provided context.
If the answer is not in the context, say "I couldn't find that information in the uploaded documents."
Always cite the source document when referencing specific information.
"""


def build_context(chunks: List[dict]) -> str:
    if not chunks:
        return "No relevant documents found."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}: {chunk['source']} | chunk {chunk['chunk_index']}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


async def ask_llm(query: str, chunks: List[dict]) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in environment")

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    context = build_context(chunks)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context from uploaded documents:\n\n{context}\n\n---\n\nQuestion: {query}",
        },
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Insurance RAG App",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    answer = data["choices"][0]["message"]["content"].strip()
    sources = list({c["source"] for c in chunks})

    return {
        "answer": answer,
        "sources": sources,
        "model": data.get("model", model),
        "chunks_used": len(chunks),
    }
