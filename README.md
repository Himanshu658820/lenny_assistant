# The Lenny Growth Assistant

An internal, AI-powered assistant grounded in **Lenny's Podcast transcripts**. It answers product & growth questions with citations, writes **Ship 30 for 30** essays, and renders **Markdown/HTML artifacts** safely inside the app.

Built as a Forward Deployed Engineer engagement: **FastAPI + PostgreSQL (pgvector) + Ollama (local)**, optional cloud providers (Anthropic / OpenAI), vanilla-JS + Tailwind frontend, one-command Docker startup.

## Features

- Grounded RAG chat with inline `(Source N)` citations + source chips
- Honest refusal when material doesn't support an answer; deterministic small-talk guard
- Sessions with independent context, sidebar history, delete; persisted in PostgreSQL
- Token-level streaming over SSE
- Ship 30 for 30 essay skill: encoded writing principles + length/format validation + one corrective retry
- Artifact generation (Markdown / HTML) with a **sandboxed in-app Artifact Viewer**
- Provider toggle (Ollama default; Anthropic/OpenAI key-gated with graceful errors)
- `/api/health/live` + `/api/health/ready`, structured logs, graceful failure modes

## Architecture

```
Browser (Vanilla JS + Tailwind, sandboxed artifact viewer)
   │  JSON / SSE
FastAPI backend
 ├─ api/      chat, chat/stream, sessions, rag, config, health
 ├─ agents/   orchestrator + skills: smalltalk, grounded_chat, ship30, artifact
 ├─ llm/      provider layer: ollama, anthropic, openai (+ factory, key-gated)
 ├─ rag/      ingest, chunking, retriever (pgvector cosine + threshold)
 └─ db/       SQLAlchemy models: chat_sessions, messages, documents, chunks
PostgreSQL + pgvector          Ollama (llama3.1:8b + nomic-embed-text)
```

Details: `docs/architecture.md` · UI rationale: `docs/design.md` · Product framing: `docs/PRD.md`

## Prerequisites

- Docker Desktop (with Compose) and Git
- Optional: NVIDIA GPU (remove the `deploy:` block in `docker-compose.yml` for CPU-only machines)

## Quickstart (one command + first-time setup)

```bash
git clone <your-repo-url> && cd lenny_growth_assistant
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
docker compose up -d --build

# First time only — load models into the container Ollama:
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text

# Index transcripts (use --limit for a fast subset; no flag = full corpus):
docker compose exec backend python -m app.rag.ingest --limit 40
```

Open **http://localhost:8000**.

> **Faster on machines that already have Ollama:** the compose file mounts `${USERPROFILE}/.ollama` (Windows) into the container, reusing models you already downloaded. On Linux/macOS, point that volume at `~/.ollama`.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `LLM_PROVIDER` | no | `ollama` | `ollama` \| `anthropic` \| `openai` |
| `OLLAMA_BASE_URL` | no | `http://ollama:11434` | container-internal Ollama |
| `OLLAMA_CHAT_MODEL` | no | `llama3.1:8b` | chat model |
| `OLLAMA_EMBED_MODEL` | no | `nomic-embed-text` | embedding model |
| `ANTHROPIC_API_KEY` | only for anthropic | *(empty)* | cloud provider key |
| `OPENAI_API_KEY` | only for openai | *(empty)* | cloud provider key |
| `DATABASE_URL` | no (set by compose) | — | Postgres DSN |
| `TOP_K` | no | `8` | chunks retrieved per query |
| `RELEVANCE_THRESHOLD` | no | `0.40` | min cosine similarity to answer |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | no | `1200` / `150` | chunking |
| `TRANSCRIPTS_DIR` | no | `data/raw/lenny_transcripts` | corpus location |

**Fallback behavior:** selecting a cloud provider without its key returns a structured `503 {"error":{"type":"llm_error",...}}` instantly; Ollama down → readable error bubble; empty retrieval → honest refusal.

## Tests

```bash
docker compose exec backend pytest
```

Manual UI plan: `docs/manual_test_plan.md`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Port 5432 already used | Change host port in compose (`"5433:5432"`) |
| `Ollama is not reachable` | Ensure Ollama service is up; check `OLLAMA_BASE_URL` |
| Slow/CPU-only inference | Remove `deploy:` GPU block; or use `llama3.2:3b` |
| `ModuleNotFoundError` after edits | Files must be `.py`, not `.py.txt` (Windows Notepad trap) |
| Long-heading ingestion crash | Fixed: `documents.title` / `chunks.heading` are `TEXT` |

## Known limitations & trade-offs

- **Local 8B model quality:** length control and occasional over-caution; mitigated by validation + retry and documented routing to cloud models for the essay skill in production.
- **Custom orchestrator** instead of the Anthropic Claude Agent SDK: the SDK cannot drive Ollama, and the demo must run locally; the orchestrator keeps identical skill boundaries and is provider-agnostic. See `docs/architecture.md`.
- **Tailwind via CDN** for prototype velocity; a build step would be added for production.

## Demo video

*(Add your YouTube link here after recording — script in `docs/demo_script.md`.)*