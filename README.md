# Insurance RAG Assistant

An **agentic Retrieval-Augmented Generation (RAG)** app for querying insurance PDF documents.
Upload policies, claim forms or any PDFs, ask questions in plain English, and get answers grounded in — and cited from — your documents.

## What makes it agentic
Instead of a single embed-and-retrieve step, each question goes through a small agent loop:

```
question ─▶ PLAN (LLM rewrites / splits into ≤3 search queries)
         ─▶ RETRIEVE (multi-query vector search, merged & de-duplicated)
         ─▶ GRADE (drop low-similarity passages)
         ─▶ ANSWER (grounded, cited) ─▶ response + trace of what the agent did
```
If the planner fails the agent falls back to the original question, and if nothing relevant is found it says so rather than hallucinating. The UI shows the queries the agent ran under each answer.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI + Python 3.11 |
| Vector DB | ChromaDB (persistent, local) |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers, runs locally) |
| LLM | OpenRouter (free models — no cost) |
| Agent | Query planning → multi-query retrieval → relevance grading (`backend/rag/agent.py`) |

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
# Edit .env and paste your OPENROUTER_API_KEY (never commit it - .env is git-ignored)

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
{ "query": "What is the deductible for comprehensive coverage?", "top_k": 6 }
```
Response:
```json
{ "answer": "...", "sources": ["policy.pdf"], "model": "...", "chunks_used": 4,
  "trace": { "queries": ["comprehensive coverage deductible"], "retrieved": 6, "kept_after_grading": 4 } }
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
│   │   ├── chunking.py      # Sentence-aware chunking (pure Python)
│   │   ├── retrieval.py     # Semantic search over ChromaDB
│   │   ├── agent.py         # Plan → retrieve → grade → answer
│   │   └── llm.py           # OpenRouter LLM calls
│   ├── tests/               # pytest suite
│   ├── chroma_db/           # Auto-created — vector store (persisted)
│   ├── requirements.txt
│   └── .env                 # local only, git-ignored
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
3. **Plan & retrieve** — The agent rewrites the question into focused queries; each is embedded and searched by cosine similarity; results are merged
4. **Grade & answer** — Irrelevant passages are dropped; the remaining chunks + question go to the OpenRouter LLM, which answers with source citations

## Tests
```bash
cd backend && pip install -r requirements-dev.txt && pytest
```
(The unit tests mock the vector store and LLM, so they need no GPU, models or API key.)

## Configuration
| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | – | Required for answers |
| `OPENROUTER_MODEL` | `google/gemma-3-27b-it:free` | Chat model |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed browser origins |
| `MAX_UPLOAD_MB` | `25` | Per-file upload limit |
| `CHROMA_PATH` | `backend/chroma_db` | Vector store location |

## Security note
Real keys must live only in `backend/.env` / `.env` (both git-ignored). If a key was ever committed, rotate it at https://openrouter.ai/keys.

