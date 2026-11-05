import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

import httpx  # noqa: E402

from rag.agent import run_agent  # noqa: E402
from rag.ingestion import delete_document, ingest_document, list_documents  # noqa: E402
from rag.retrieval import retrieve_chunks  # noqa: E402

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))

app = FastAPI(
    title="Insurance RAG API",
    description="Upload PDFs and ask questions - agentic retrieval powered by OpenRouter LLMs",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    model: str
    chunks_used: int
    trace: dict = {}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload one or more PDF files and index them into the vector store."""
    results = []
    for file in files:
        name = file.filename or "unnamed"
        if not name.lower().endswith(".pdf"):
            results.append({"filename": name, "status": "skipped_not_pdf"})
            continue
        content = await file.read()
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            results.append({"filename": name, "status": "error", "detail": f"File exceeds {MAX_UPLOAD_MB} MB limit"})
            continue
        try:
            # Parsing + embedding is CPU-bound: keep it off the event loop.
            results.append(await run_in_threadpool(ingest_document, name, content))
        except Exception as e:
            results.append({"filename": name, "status": "error", "detail": str(e)})
    return {"results": results}


@app.get("/api/documents")
async def get_documents():
    """List all indexed documents with chunk counts."""
    docs = await run_in_threadpool(list_documents)
    return {"documents": docs, "total": len(docs)}


@app.delete("/api/documents/{filename:path}")
async def remove_document(filename: str):
    """Delete a document and all its chunks from the vector store."""
    result = await run_in_threadpool(delete_document, filename)
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
    return result


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Answer a question with the agentic RAG pipeline (plan -> retrieve -> grade -> answer)."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        return await run_agent(request.query, top_k=request.top_k)
    except ValueError as e:  # e.g. missing API key
        raise HTTPException(status_code=500, detail=str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"LLM provider returned {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")


@app.get("/api/search")
async def search_chunks(q: str = Query(min_length=1), top_k: int = Query(5, ge=1, le=20)):
    """Debug endpoint: retrieve raw chunks for a query."""
    return {"query": q, "chunks": await run_in_threadpool(retrieve_chunks, q, top_k)}
