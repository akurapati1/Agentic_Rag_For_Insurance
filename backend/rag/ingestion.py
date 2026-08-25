import hashlib
import re
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "documents"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

_embedder: SentenceTransformer | None = None
_client: chromadb.PersistentClient | None = None
_collection = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def get_collection():
    global _client, _collection
    if _client is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    if _collection is None:
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    # Split on sentences, then group into chunks
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    chunks, current, current_len = [], [], 0
    for sent in sentences:
        sent_len = len(sent)
        if current_len + sent_len > chunk_size and current:
            chunks.append(" ".join(current))
            # keep overlap
            overlap_chars, overlap_sents = 0, []
            for s in reversed(current):
                if overlap_chars + len(s) > overlap:
                    break
                overlap_sents.insert(0, s)
                overlap_chars += len(s)
            current = overlap_sents
            current_len = overlap_chars
        current.append(sent)
        current_len += sent_len
    if current:
        chunks.append(" ".join(current))
    return [c.strip() for c in chunks if c.strip()]


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
        chunk_hash = hashlib.md5(f"{filename}_{i}_{chunk[:50]}".encode()).hexdigest()
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
