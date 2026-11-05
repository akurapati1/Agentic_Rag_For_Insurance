import hashlib
import os
from pathlib import Path
from typing import List

from .chunking import CHUNK_OVERLAP, CHUNK_SIZE, chunk_text  # noqa: F401  (re-exported)

# Heavy ML dependencies are imported lazily so the API/unit tests start instantly.
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", Path(__file__).parent.parent / "chroma_db"))
COLLECTION_NAME = "documents"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_embedder = None
_client = None
_collection = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def get_collection():
    global _client, _collection
    if _client is None:
        import chromadb

        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    if _collection is None:
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def extract_text_from_pdf(file_bytes: bytes) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def ingest_document(filename: str, file_bytes: bytes) -> dict:
    """Extract, chunk, embed, and store a PDF. Always re-indexes."""
    collection = get_collection()
    embedder = get_embedder()

    # Remove existing docs for this filename
    existing = collection.get(where={"source": filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    # Extract & chunk
    text = extract_text_from_pdf(file_bytes)
    chunks = chunk_text(text)

    if not chunks:
        return {"filename": filename, "chunks": 0, "status": "no_text_extracted"}

    # Embed
    embeddings = embedder.encode(chunks, show_progress_bar=False).tolist()

    # Build IDs and metadata
    ids, metadatas = [], []
    for i, chunk in enumerate(chunks):
        chunk_hash = hashlib.sha1(f"{filename}_{i}_{chunk[:50]}".encode()).hexdigest()
        ids.append(chunk_hash)
        metadatas.append({"source": filename, "chunk_index": i})

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    return {"filename": filename, "chunks": len(chunks), "status": "indexed"}


def list_documents() -> List[dict]:
    """Return unique documents with chunk counts."""
    collection = get_collection()
    result = collection.get()
    counts: dict[str, int] = {}
    for meta in result["metadatas"] or []:
        src = meta.get("source", "unknown")
        counts[src] = counts.get(src, 0) + 1
    return [{"filename": k, "chunks": v} for k, v in sorted(counts.items())]


def delete_document(filename: str) -> dict:
    collection = get_collection()
    existing = collection.get(where={"source": filename})
    if not existing["ids"]:
        return {"deleted": False, "reason": "not_found"}
    collection.delete(ids=existing["ids"])
    return {"deleted": True, "filename": filename}
