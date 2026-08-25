# Architecture — The Lenny Growth Assistant

## 1. Overview

Three Docker services; a classic RAG + skills architecture with a provider-agnostic LLM layer.

```
┌──────────────────────────── Browser ────────────────────────────┐
│  Vanilla JS + Tailwind · marked.js · DOMPurify                  │
│  [Sidebar: sessions/provider] [Chat] [Artifact Viewer (sandbox)]│
└───────────────┬───────────────────────────────▲─────────────────┘
        JSON / SSE (POST /api/chat/stream)      │
┌───────────────▼───────────────────────────────┴─────────────────┐
│                        FastAPI (backend)                        │
│  api/        health · config · sessions · chat · rag            │
│  agents/     orchestrator → smalltalk | grounded_chat | ship30 | artifact
│  llm/        factory → OllamaProvider | AnthropicProvider | OpenAIProvider
│  rag/        ingest · chunking · retriever (pgvector cosine)    │
│  db/         SQLAlchemy models · init_db (CREATE EXTENSION vector)
└───────┬───────────────────────────────────────────┬─────────────┘
        │ psycopg                                   │ HTTP
┌───────▼───────────────────┐           ┌───────────▼─────────────┐
│ PostgreSQL 16 + pgvector  │           │ Ollama (container)      │
│ chat_sessions, messages,  │           │ llama3.1:8b (chat)      │
│ documents, chunks(vector) │           │ nomic-embed-text (embed)│
└───────────────────────────┘           └─────────────────────────┘
```

## 2. Component boundaries

| Package | Responsibility | Must not know about |
|---|---|---|
| `api/` | HTTP contracts, validation, SSE streaming, structured errors | embedding math, prompts |
| `agents/` | intent routing + skill execution (prompts, validation) | HTTP, DB schema |
| `llm/` | provider adapters (chat, chat_stream, embed) | skills, retrieval |
| `rag/` | chunking, ingestion/refresh, retrieval/scoring | providers, HTTP |
| `db/` | models + session factory | business logic |
| `core/` | settings (pydantic-settings), error taxonomy | everything else |

## 3. Database schema

| Table | Columns (key) | Purpose |
|---|---|---|
| `chat_sessions` | id UUID PK, title, llm_provider, created_at, updated_at | session identity + sidebar |
| `messages` | id UUID PK, session_id FK→sessions (CASCADE), role, content, sources JSONB, meta JSONB, created_at | full history; `meta` carries skill/provider/model/latency/supported/checks/artifact |
| `documents` | id UUID PK, source_path UNIQUE, title TEXT, sha256, word_count, ingested_at | refresh detection + source tracing |
| `chunks` | id UUID PK, document_id FK→documents (CASCADE), chunk_index, heading TEXT, content TEXT, embedding vector(768), created_at | retrieval units |

Schema is created by `init_db()` at startup (`CREATE EXTENSION IF NOT EXISTS vector` + `create_all`). **Trade-off:** no Alembic migrations in the prototype; for production we would freeze the schema and add migration tooling.

## 4. API endpoints

| Method & path | Purpose | Notes |
|---|---|---|
| `GET /api/health/live` | liveness | always 200 |
| `GET /api/health/ready` | readiness | checks DB + active provider; 503 when degraded |
| `GET /api/config/llm` | provider matrix | current provider + which keys are configured |
| `POST /api/sessions` | create session | |
| `GET /api/sessions` | list w/ message counts | ordered by recency |
| `GET /api/sessions/{id}/messages` | history | 404 structured if missing |
| `DELETE /api/sessions/{id}` | delete chat | 204 |
| `POST /api/chat` | non-streaming chat | used by automated tests |
| `POST /api/chat/stream` | streaming chat | SSE; see §7 |
| `GET /api/rag/stats` | corpus counts | observability |
| `POST /api/rag/ingest?limit=N` | (re)ingest | sha256-based refresh |
| `GET /api/rag/search?q=&top_k=` | raw retrieval | debugging + evals |

Contracts are Pydantic models (`api/schemas.py`); validation errors → 422; domain errors → `{"error":{"type","message"}}` with proper status (404/503).

## 5. Ingestion & retrieval flow

1. **Load:** `TRANSCRIPTS_DIR` scanned recursively for `*.md` (sorted; optional `--limit` for subsets).
2. **Refresh:** file sha256 compared to `documents.sha256` → skip / replace (old chunks cascade-deleted). Idempotent and incremental.
3. **Chunk:** heading-aware splitter (target 1200 chars, 150 overlap; chunks < 80 chars dropped); heading stored per chunk.
4. **Embed:** *metadata-augmented* input — `Episode: {title}\nSection: {heading}\n{content}` — so name-based queries ("According to Eric Ries…") match the right document even when the chunk body lacks the name. `nomic-embed-text` (768-dim), batched.
5. **Retrieve:** cosine distance (`<=>`) ordered, `TOP_K` (default 8); score = 1 − distance; sources deduped by title (best score kept).
6. **Grounding gate:** top score ≥ `RELEVANCE_THRESHOLD` (default 0.40) → *supported*, else deterministic refusal (no LLM call).
7. **Trace:** every source chip carries `title`, `source_path`, `heading`, `score`; `(Source N)` in answers maps to chip order.

**Precision/recall stance:** we prefer honest refusal over forced answers; both knobs are env-tunable without code changes.

## 6. Agent layer & routing

Routing order (first match wins):

| Skill | Trigger | Behavior |
|---|---|---|
| `smalltalk` | regex guard (greetings, "my name is…", "who are you", thanks, help) | deterministic instant reply; zero GPU |
| `ship30` | "ship 30", "essay" | grounded retrieval → essay → validation (1000–1500 words, headings, bullets, bold, takeaway) → one corrective retry → Markdown artifact |
| `artifact` | "artifact", "html", "one-pager", "dashboard", "cheat sheet" | Markdown or no-JS HTML document from conversation + retrieval |
| `grounded_chat` | default | strict grounding prompt + citations + anti-bleed/consistency rules |

**Trade-off — custom orchestrator vs Anthropic Claude Agent SDK:** the SDK cannot drive Ollama, and the brief mandates a local-Ollama demo. We therefore implemented the same boundaries (discrete skills, explicit routing, provider injection) in a provider-agnostic orchestrator. Production path: swap `grounded_chat`/`ship30` internals to the SDK when `LLM_PROVIDER=anthropic`, keeping API and UI unchanged.

## 7. Streaming protocol (SSE)

`POST /api/chat/stream` → `text/event-stream`:

| Event | Payload | When |
|---|---|---|
| `session` | `{session_id}` | first (allows UI to bind session) |
| `sources` | `[source…]` | after retrieval |
| `token` | `{text}` | per model token (grounded_chat) |
| `artifact` | `{type,title,content,word_count}` | ship30/artifact skills |
| `error` | `{message}` | provider/retrieval failure mid-stream |
| `done` | full response object | last; UI finalizes markdown render |

Ship30/artifact deliver whole (they must be validated before display); chat streams token-by-token.

## 8. Security model

| Surface | Strategy | Permits | Blocks |
|---|---|---|---|
| HTML artifacts | `<iframe sandbox="" srcdoc=…>` | static HTML/CSS rendering | scripts, forms, popups, top-navigation, same-origin access |
| Markdown (artifacts & chat) | marked.js → **DOMPurify** sanitize | safe formatting | script/event-handler injection |
| Secrets | env-only; `.env` gitignored; `.env.example` safe | — | committed keys |
| Data egress | local mode makes **zero external calls** | Ollama inside compose | any third-party API unless a cloud provider is explicitly selected |

## 9. Observability

Named loggers (`lenny.chat`, `lenny.orchestrator`, `lenny.ingest`, `lenny.retrieval`, `lenny.skill.*`) emit request-scoped facts: session id, provider, skill, supported flag, latency, ingestion summaries. Health endpoints expose DB + provider status for ops.

## 10. Resilience matrix

| Failure | Behavior |
|---|---|
| Cloud key missing | instant structured 503, UI error bubble, no crash |
| Ollama unreachable | `LLMProviderError` → readable bubble; readiness 503 |
| Model timeout | 180 s cap (stream: no read-timeout mid-generation) → error event |
| Empty/weak retrieval | deterministic refusal; no hallucinated fallback |
| DB down | readiness 503 with `database: error`; API errors structured |
| Oversized heading/title | `TEXT` columns; ingestion never truncates meaning |

## 11. Deployment topology

| Service | Image | Ports | Volumes |
|---|---|---|---|
| `db` | pgvector/pgvector:pg16 | 5432 | `db_data` |
| `ollama` | ollama/ollama:latest | internal only | `${USERPROFILE}/.ollama` (reuse host models) |
| `backend` | build `./backend` | 8000 | `./backend/app`, `./frontend`, `./data` (dev live-mounts) |

GPU passthrough via `deploy.resources.reservations.devices` (remove block for CPU-only hosts). One-command startup: `docker compose up -d --build` + documented model/ingest steps.

## 12. Trade-offs & future work

- `create_all` → Alembic for production schema evolution.
- Tailwind CDN → build step for offline/production.
- Retrieval → optional cross-encoder rerank; clickable source chips with excerpt popovers.
- Ship30 on local 8B shows length-control limits → route essays to cloud models in production (documented in PRD).