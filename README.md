# Insurance RAG Assistant

A full-stack Retrieval-Augmented Generation (RAG) app for querying insurance PDF documents.
Upload any PDFs, ask questions in plain English, and get accurate answers grounded in your documents.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI + Python 3.11 |
| Vector DB | ChromaDB (persistent, local) |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers, runs locally) |
| LLM | OpenRouter (free models — no cost) |

---

## Quick Start (Local Dev — No Docker)

### 1. Get a free OpenRouter API key
Sign up at https://openrouter.ai — it's free with rate limits.

### 2. Backend setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Set your key:
cp .env.example .env
# Edit .env and paste your OPENROUTER_API_KEY

uvicorn main:app --reload --port 8000
```

Backend runs at http://localhost:8000  
API docs at http://localhost:8000/docs

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

---

## Quick Start (Docker)

```bash
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

docker-compose up --build
```

Open http://localhost:5173

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload one or more PDFs |
| GET | `/api/documents` | List indexed documents |
| DELETE | `/api/documents/{filename}` | Remove a document |
| POST | `/api/chat` | Ask a question (RAG) |
| GET | `/api/search?q=...` | Debug: raw chunk retrieval |
| GET | `/api/health` | Health check |

### Example chat request
```json
POST /api/chat
{
  "query": "What is the deductible for comprehensive coverage?",
  "top_k": 6
}
```

---

## Free OpenRouter Models

Change `OPENROUTER_MODEL` in `.env` to switch models:

```
google/gemma-3-27b-it:free       ← default (good quality)
meta-llama/llama-3.3-70b-instruct:free
mistralai/mistral-7b-instruct:free
deepseek/deepseek-r1:free
```

---

## Project Structure

```
Agentic_Rag_For_Insurance/
├── backend/
│   ├── main.py              # FastAPI app + all endpoints
│   ├── rag/
│   │   ├── ingestion.py     # PDF parsing, chunking, ChromaDB indexing
│   │   ├── retrieval.py     # Semantic search over ChromaDB
│   │   └── llm.py           # OpenRouter LLM calls
│   ├── chroma_db/           # Auto-created — vector store (persisted)
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Root layout
│   │   ├── api.js           # All fetch calls to backend
│   │   └── components/
│   │       ├── ChatPanel.jsx      # Chat UI + message history
│   │       ├── DocumentPanel.jsx  # Upload dropzone + document list
│   │       └── MessageBubble.jsx  # Individual message rendering
│   ├── index.html
│   ├── vite.config.js       # Vite + /api proxy to :8000
│   └── package.json
└── docker-compose.yml
```

---

## How It Works

1. **Upload** — PDF bytes → PyMuPDF text extraction → sentence chunking (800 chars, 150 overlap)  
2. **Index** — Each chunk embedded with `all-MiniLM-L6-v2` → stored in ChromaDB with filename metadata  
3. **Query** — User question embedded → cosine similarity search → top-6 chunks retrieved  
4. **Answer** — Chunks + question sent to OpenRouter LLM → streamed answer with source citations

