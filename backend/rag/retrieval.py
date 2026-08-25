from typing import List
from .ingestion import get_collection, get_embedder


def retrieve_chunks(query: str, top_k: int = 6) -> List[dict]:
    """Embed query and return top-k relevant chunks with metadata."""
    collection = get_collection()
    embedder = get_embedder()

    total = collection.count()
    if total == 0:
        return []

    query_embedding = embedder.encode([query], show_progress_bar=False).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "similarity": round(1 - dist, 4),  # cosine distance → similarity
        })

    return chunks
