# RAG Document Analysis

> Retrieval-Augmented Generation pipeline for PDF documents. Upload a PDF, ask questions in Turkish, get answers grounded in source chunks with page references.

A production-shaped RAG service built to study real-world trade-offs: async ingestion queues, local embeddings, vector persistence, streaming LLM responses, and multi-platform deployment.

---

## Overview

The system answers natural-language questions about a user's uploaded PDFs. It does not hallucinate freely — every answer is grounded in retrieved chunks, and the user can inspect which page and passage each citation came from.

```
                                +-------------------+
       +----------+    HTTP     |     FastAPI       |   OpenAI SDK    +------------+
       |  Next.js | -----------> |  (uvicorn: 8000)  | ---------------> | OpenRouter |
       | (3000)   |   /api/      |                   |                  |  gpt-4o-mini|
       +----------+   backend    |  /documents/*     |                  +------------+
            |                    |  /jobs/{id}       |
            | SSE chat           |  /chat/stream     |   sentence-      +-----------+
            v                    |                   | --transformers->|  Chroma   |
       +----------+              |  worker:          |                  |  (volume) |
       |  Browser | <----------- |  Celery (CPU)     |                  +-----------+
       +----------+    job poll  |                   |
                                +-------------------+
```

### Pipeline

**Ingestion (async via Celery + Redis):**
1. `POST /documents/upload` saves the PDF and returns `202 Accepted` with a `job_id` immediately.
2. A Celery worker picks up the task, parses pages with `pymupdf`, splits with `RecursiveCharacterTextSplitter`, embeds with `BAAI/bge-small-en-v1.5`, and writes vectors to Chroma with `document_id` metadata.
3. The frontend polls `GET /jobs/{id}` for progress.

**Retrieval + generation (sync, SSE):**
1. Question is embedded with the same BGE model.
2. Top-K (default 5) chunks are fetched from Chroma, optionally filtered by `document_id`.
3. Chunks are formatted into a context block; a system prompt instructs the model to answer only from the context.
4. OpenRouter streams tokens back to the client over Server-Sent Events with three event types: `sources`, `token`, `done`.

---

## Tech stack

| Layer            | Choice                              | Why                                                 |
|------------------|-------------------------------------|-----------------------------------------------------|
| Backend          | FastAPI 0.115, Python 3.11          | Async, type-safe, OpenAPI built-in                  |
| Job queue        | Celery 5 + Redis 7                  | Decouples ingestion from request lifecycle          |
| PDF parsing      | `pymupdf`                           | Fast, no system deps, handles digital PDFs          |
| Chunking         | `RecursiveCharacterTextSplitter`    | Language-agnostic, predictable boundaries           |
| Embeddings       | `BAAI/bge-small-en-v1.5` (local)    | 120 MB, multilingual, no API cost                   |
| Vector store     | ChromaDB (HNSW + cosine)            | Zero-config, persistent, metadata filtering         |
| LLM              | OpenRouter `openai/gpt-4o-mini`     | OpenAI-compatible API, flexible model selection     |
| Frontend         | Next.js 15 (App Router), React 19   | Streaming SSE proxy, server-side rewrite to backend |
| Styling          | Tailwind + Framer Motion            | Glassmorphism, smooth state transitions             |

---

## Project layout

```
rag-document-analysis/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app
│   │   ├── celery_app.py          # Celery configuration
│   │   ├── core/config.py         # Pydantic Settings
│   │   ├── api/documents.py       # HTTP endpoints
│   │   ├── schemas/documents.py   # Request/response models
│   │   ├── tasks/ingestion.py     # Celery ingestion task
│   │   └── services/
│   │       ├── pdf_parser.py      # pymupdf
│   │       ├── chunker.py         # Recursive splitter
│   │       ├── embedder.py        # BGE-small
│   │       ├── llm.py             # OpenRouter
│   │       ├── vector_store.py    # Chroma adapter
│   │       ├── ingestion.py       # PDF → DB pipeline
│   │       └── rag.py             # retrieve → prompt → generate
│   ├── data/                      # uploads + chroma (gitignored)
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Landing
│   │   │   ├── layout.tsx         # Nav + global styles
│   │   │   ├── documents/         # Drag & drop + async progress
│   │   │   ├── chat/              # SSE chat with source drawer
│   │   │   └── api/chat/          # Next → backend SSE proxy
│   │   └── lib/
│   │       ├── api.ts             # Backend client
│   │       ├── storage.ts         # localStorage document list
│   │       └── types.ts
│   ├── public/images/logo.svg
│   ├── package.json
│   ├── tailwind.config.ts
│   └── .env.example
├── docker-compose.yml             # Redis + backend + worker
├── .env.example
└── README.md
```

---

## Quick start

### Option A: Docker (recommended)

Single-command stack with Redis, backend API, and Celery worker. Frontend runs locally with `npm run dev` for fast iteration.

Prerequisites: Docker Desktop, Node.js 20+, an OpenRouter API key.

```powershell
# 1. Configure secrets
copy .env.example .env
# Edit .env and paste your OPENROUTER_API_KEY

# 2. Start Redis + backend + worker
docker compose up --build

# 3. In a second terminal, start the frontend
cd frontend
npm install
copy .env.example .env.local
npm run dev

# 4. Open
#    http://localhost:3000     (frontend)
#    http://localhost:8000/docs (API docs)
```

First build pulls `python:3.11-slim`, `node:20-alpine`, `redis:7-alpine` and downloads the BGE model (~120 MB). Expect 3-5 minutes on a cold cache; subsequent restarts take seconds.

Data persistence: Chroma vectors and uploaded PDFs live in the `rag-data` named volume. Survives container restarts. Remove with `docker compose down -v`.

### Option B: Manual (no Docker)

Four terminals, one for each process.

```powershell
# Terminal 1 - Redis
# Install from https://github.com/microsoftarchive/redis/releases or use WSL
redis-server

# Terminal 2 - Backend
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env   # fill in OPENROUTER_API_KEY
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 3 - Celery worker
cd backend
.\.venv\Scripts\python.exe -m celery -A app.celery_app worker --loglevel=info --concurrency=1

# Terminal 4 - Frontend
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

For local development without Redis, set `CELERY_EAGER=true` in `backend/.env` to run ingestion synchronously inside the API process. Do not use this in production.

---

## API

| Method | Path                          | Description                                                |
|--------|-------------------------------|------------------------------------------------------------|
| GET    | `/health`                     | Liveness check                                             |
| POST   | `/documents/upload`           | Multipart upload, returns `202` with `job_id`              |
| GET    | `/jobs/{job_id}`              | Poll ingestion progress (`PENDING`/`PROGRESS`/`SUCCESS`)   |
| GET    | `/documents/search?q=...`     | Top-K similar chunks (debugging)                           |
| POST   | `/documents/chat`             | Sync RAG answer with sources                               |
| POST   | `/documents/chat/stream`      | SSE streaming chat (`sources` → `token` × N → `done`)      |

### Upload flow

```http
POST /documents/upload
Content-Type: multipart/form-data

file=@document.pdf
```

Response (`202 Accepted`):
```json
{
  "job_id": "a1b2c3-...",
  "document_id": "uuid",
  "filename": "document.pdf",
  "status_url": "/jobs/a1b2c3-..."
}
```

Poll the status URL:
```json
{ "job_id": "...", "state": "PROGRESS", "stage": "parse + chunk + embed", "percent": 30 }
{ "job_id": "...", "state": "SUCCESS", "result": { "document_id": "...", "pages": 12, "chunks": 87 } }
```

### SSE event format

```
event: sources
data: [{"text":"...","page_number":3,"document_id":"...","score":0.82}]

event: token
data: "Yapay"

event: token
data: " zeka"

event: done
data: {}
```

---

## Configuration

All settings are read from environment variables, typically loaded from `backend/.env`.

| Variable                          | Default                              | Notes                          |
|-----------------------------------|--------------------------------------|--------------------------------|
| `OPENROUTER_API_KEY`              | (required)                           | LLM API key                    |
| `OPENROUTER_BASE_URL`             | `https://openrouter.ai/api/v1`       |                                |
| `LLM_MODEL`                       | `openai/gpt-4o-mini`                 | Any OpenRouter model ID        |
| `BGE_MODEL_NAME`                  | `BAAI/bge-small-en-v1.5`             | Any sentence-transformers model |
| `BGE_DEVICE`                      | `cpu`                                | `cpu` or `cuda`                |
| `BGE_BATCH_SIZE`                  | `16`                                 |                                |
| `CHUNK_SIZE`                      | `800`                                | Character count                |
| `CHUNK_OVERLAP`                   | `120`                                |                                |
| `CHROMA_PERSIST_DIR`              | `./data/chroma`                      |                                |
| `MAX_UPLOAD_MB`                   | `20`                                 |                                |
| `CELERY_BROKER_URL`               | `redis://127.0.0.1:6379/0`           |                                |
| `CELERY_RESULT_BACKEND`           | `redis://127.0.0.1:6379/1`           |                                |
| `CELERY_EAGER`                    | unset                                | `true` skips Redis (dev only)  |

---

## Technology choices and rationale

- **BGE-small over BGE-M3**: M3 is 2.3 GB and takes 10+ minutes to download; small is 120 MB and downloads in 1-2 minutes. Turkish quality is weaker but sufficient for demonstration. Switching to `intfloat/multilingual-e5-base` is a one-line config change.

- **OpenRouter over direct OpenAI**: the OpenAI SDK is OpenRouter-compatible via `base_url` override, giving us the option to swap providers (Anthropic, Mistral, local) without code changes. No OpenAI account balance required.

- **Chroma over Qdrant/Pinecone**: zero devops, persistent by default, sufficient for a single-node demo. Migration to Qdrant self-hosted is straightforward when horizontal scaling becomes necessary.

- **Recursive splitter over semantic chunking**: language-agnostic, fast, predictable. Semantic chunking via LlamaIndex can be added later if retrieval quality degrades on long, structured documents.

- **Celery over FastAPI BackgroundTasks**: BackgroundTasks die with the request process and do not survive restarts. Celery persists tasks in Redis, so a worker crash mid-ingestion is recoverable via task retry.

- **SSE over WebSocket**: chat is a one-way stream from server to client. SSE works over plain HTTP, supports automatic browser reconnection, and is sufficient for token streaming.

---

## Known limitations

- **Digital PDFs only.** Scanned documents require OCR; candidates are `docling` and `marker`.
- **No authentication.** All uploaded documents are visible to any client of the same backend instance. Multi-tenancy requires JWT + per-user `document_id` filtering.
- **Single worker.** `worker_concurrency=1` because embedding is CPU-bound; raising this without sufficient cores causes thrashing. A GPU backend would unlock parallelism.
- **No rate limiting.** OpenRouter's per-key limits are the only constraint. Add `slowapi` or `fastapi-limiter` if exposing publicly.
- **Embedding model is fixed per process.** Switching models at runtime requires a worker restart.

---

## Roadmap

- [ ] OCR support for scanned PDFs
- [ ] JWT auth and per-user document isolation
- [ ] Document listing page (browse, delete, rename)
- [ ] Streaming cancellation button (AbortController already wired)
- [ ] Better multilingual embedding (`intfloat/multilingual-e5-base`)
- [ ] Qdrant migration guide for production scale
- [ ] Evaluation harness (RAGAS or custom) for retrieval quality

---

## License

MIT
