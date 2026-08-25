# PRD — The Lenny Growth Assistant

## 1. Discovery brief

### 1.1 User and problem
**Primary user:** product & growth team members (PMs, growth marketers, founders).
**Job to be done:** get reliable, sourced answers and reusable written content from 300+ podcast transcripts, fast.
**Pain removed:** manually searching transcripts; prompt-engineering to get grounded answers; reformatting insights into essays/one-pagers; distrusting un-cited AI output.

### 1.2 Success metric
- ≥ 80% of on-topic questions answered with ≥ 1 correct transcript citation (manual eval set).
- 0 unsupported factual claims on off-topic probes (refusal rate over forcing rate).
- Time-to-first-token < 3 s on GPU hardware; full answer < 30 s.
- Fresh evaluator reaches a working chat in < 10 minutes using only the README.

### 1.3 Assumptions
- Users are internal; no auth/PII handling required for the prototype.
- Transcripts are the trusted source of truth; the web is out of scope.
- The demo must run on a laptop-class machine → local Ollama is the default provider.
- Artifacts are static documents (no interactive JS needed) → strict sandboxing is safe.

### 1.4 Scope choices
**Included:** grounded chat + citations; sessions & persistence; streaming; Ship 30 skill with validation; Markdown/HTML artifacts + sandboxed viewer; provider toggle; Docker one-command startup; health/observability; tests & docs.
**Excluded (and why):** authentication & multi-tenancy (internal prototype); live web search (grounding contract is transcripts-only); production scaling/queues (out of scope for evaluation); streaming for Ship 30/artifact skills (they must be validated whole before delivery).

### 1.5 Risks and trade-offs
| Risk | Mitigation |
|---|---|
| Hallucination | Strict grounding prompt, citation requirement, deterministic refusal below relevance threshold, small-talk guard |
| Local-model quality (length, caution) | Validation + one corrective retry for essays; document cloud-model routing for production |
| Latency | SSE streaming; embeddings batched; GPU passthrough |
| Cost | Local-first; cloud providers are opt-in |
| Data leakage | Local mode makes zero external calls; keys never leave env |
| Unsafe artifact rendering | `iframe sandbox=""` (no scripts/forms/nav) + DOMPurify for Markdown |
| Retrieval precision vs recall | Tunable `TOP_K` / `RELEVANCE_THRESHOLD`; metadata-augmented embeddings; honest refusal preferred |

## 2. Flows
1. **Ask:** user message → session created/loaded → retrieval → grounded streamed answer with sources.
2. **Refuse:** below-threshold retrieval → deterministic honest refusal (no sources).
3. **Essay:** route to `ship30` → grounded retrieval → essay generation → validation (1000–1500 words, headings, bullets, bold, takeaway) → retry if needed → Markdown artifact in viewer.
4. **Artifact:** route to `artifact` → Markdown/HTML generation → sandboxed render.

## 3. Acceptance criteria (key)
- New chat keeps independent context; history persists across reloads.
- Every factual answer shows ≥ 1 source chip; `(Source N)` maps to chip order.
- Off-topic probes ("meme stocks", "pizza recipe") refuse without inventing facts.
- HTML artifacts containing `<script>` render inert.
- Missing cloud key → instant structured 503; Ollama down → readable error; DB down → readiness 503.
- `docker compose up --build` + documented steps reproduce the system from a clean clone.

## 4. Implementation plan (as executed)
Phase 1 scaffold & health → Phase 2 schema/ingestion/retrieval → Phase 3 sessions/chat/providers/orchestrator → Phase 4 skills/artifacts/UI/streaming → Phase 5 tests/docs/handoff.