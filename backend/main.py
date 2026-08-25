import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from rag.ingestion import ingest_document, list_documents, delete_document
from rag.retrieval import retrieve_chunks
from rag.llm import ask_llm

app = FastAPI(
    title="Insurance RAG API",
    description="Upload PDFs and ask questions powered by OpenRouter LLMs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    top_k: int = 6

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    model: str
    chunks_used: int

# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload one or more PDF files and index them into the vector store."""
    results = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"filename": file.filename, "status": "skipped_not_pdf"})
            continue
        content = await file.read()
        try:
            result = ingest_document(file.filename, content)
            results.append(result)
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "detail": str(e)})
    return {"results": results}


@app.get("/api/documents")
async def get_documents():
    """List all indexed documents with chunk counts."""
    docs = list_documents()
    return {"documents": docs, "total": len(docs)}


@app.delete("/api/documents/{filename:path}")
async def remove_document(filename: str):
    """Delete a document and all its chunks from the vector store."""
    result = delete_document(filename)
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
    return result


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Answer a question using RAG over the indexed documents."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    chunks = retrieve_chunks(request.query, top_k=request.top_k)
    if not chunks:
        return ChatResponse(
            answer="No documents have been uploaded yet. Please upload some PDF files first.",
            sources=[],
            model="none",
            chunks_used=0,
        )

    try:
        response = await ask_llm(request.query, chunks)
        return ChatResponse(**response)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")


@app.get("/api/search")
async def search_chunks(q: str, top_k: int = 5):
    """Debug endpoint: retrieve raw chunks for a query."""
    chunks = retrieve_chunks(q, top_k=top_k)
    return {"query": q, "chunks": chunks}
