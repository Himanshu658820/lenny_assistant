# Design — The Lenny Growth Assistant

## 1. Principles

1. **Grounded and verifiable first.** Every factual answer shows its evidence (source chips) and inline `(Source N)` citations; evidence sits one glance below the answer, never hidden.
2. **Honest over impressive.** Refusals are first-class UI states. The assistant never bluffs; small talk gets an instant deterministic reply.
3. **Calm, professional tool.** Neutral slate palette, single indigo accent, generous spacing — an internal product, not a marketing page.
4. **Fail visibly, kindly.** Every failure mode renders as a readable, actionable message (error bubble), never a dead screen or silent spinner.
5. **Progressive disclosure.** Artifacts open on demand in a side pane; sources collapse into chips; advanced config lives in the sidebar.

## 2. Information architecture

### 2.1 Layout regions

```
┌─────────────┬────────────────────────────────┬─────────────────────────┐
│  SIDEBAR    │          CHAT COLUMN           │     ARTIFACT PANE       │
│  (288 px)   │         (flexible)             │   (50%, on demand)      │
├─────────────┼────────────────────────────────┼─────────────────────────┤
│ + New Chat  │ header: session title          │ header: artifact title  │
│             │                                │         TYPE • words    │
│ MODEL       │ ┌────────────────────────────┐ │ ┌─────────────────────┐ │
│ PROVIDER    │ │ assistant bubble           │ │ │ sanitized Markdown  │ │
│ [ Ollama ▾ ]│ │  answer (streamed)         │ │ │        — or —       │ │
│             │ │  Sources: [chip] [chip]    │ │ │ sandboxed <iframe>  │ │
│ SESSIONS    │ │  📄 View artifact          │ │ │ (HTML/CSS only)     │ │
│ ┌─────────┐ │ └────────────────────────────┘ │ └─────────────────────┘ │
│ │ chat  🗑 │ │                 ┌────────────┐ │                         │
│ │ …     🗑 │ │                 │ user bubble│ │                         │
│ └───────── │                 └────────────┘ │                         │
│             │ ┌────────────────────────────┐ │                         │
│             │ │ composer  (Enter = send)   │ │                         │
│             │ └────────────────────────────┘ │                         │
└─────────────┴────────────────────────────────┴─────────────────────────┘
```

### 2.2 Region responsibilities

| Region | Contains | Job | Backend it talks to |
|---|---|---|---|
| **Sidebar** | New Chat, provider select, session list (hover-to-delete) | Session lifecycle + visible model toggle (requirement #13) | `POST/GET/DELETE /api/sessions`, `GET /api/config/llm` |
| **Chat column** | Session title header, message stream, composer | The conversation: streaming answers, citations, error/refusal states | `POST /api/chat/stream`, `GET /api/sessions/{id}/messages` |
| **Artifact pane** | Title, type/word-count badge, close button, render surface | Safe native rendering of Markdown/HTML artifacts beside the chat (requirement 4.3) | none extra — artifact arrives inside the chat response |

### 2.3 Visual hierarchy & attention order

1. **Composer** — the primary action surface; always visible, Enter-to-send.
2. **Streaming answer** — live token bubble holds attention while generating.
3. **Sources row** — one glance down for trust verification (the "footnote" pattern).
4. **Artifact pane** — opens only on demand; never steals the conversation.
5. **Sidebar** — context switching, deliberately low-salience (dark, quiet).

### 2.4 Navigation & state flow

- **New Chat** → empty state with suggested prompts.
- **Send** → live streaming bubble → finalized Markdown render on `done`.
- **`artifact` event** → pane opens with sandboxed render; **✕** closes it.
- **Session click** → history loads (artifacts re-openable per message); pane closes.
- **Delete (🗑)** → native confirm → list refreshes; deleting the active session resets to New Chat.
- **Provider change** → applies to the *next* request; misconfigured providers surface as readable error bubbles, never silent failures.

### 2.5 Frontend component tree

```
index.html
├─ aside (sidebar)
│   ├─ button#btn-new-chat
│   ├─ select#provider-select          ← visible LLM toggle
│   └─ nav#session-list
│       └─ row: [session title button][delete button (aria-label)]
├─ main (chat column)
│   ├─ header#chat-title
│   ├─ div#chat-messages
│   │   ├─ #empty-state                ← zero-data state
│   │   ├─ message bubbles             ← user / assistant / error variants
│   │   └─ live stream bubble          ← transient, replaced on `done`
│   └─ form#chat-form (textarea + Send)
└─ aside#artifact-pane (hidden by default)
    ├─ header: #artifact-title, #artifact-meta, #btn-close-artifact
    └─ #artifact-content
        ├─ sanitized Markdown container (marked + DOMPurify)
        └─ sandboxed iframe (sandbox="") for HTML artifacts
```

## 3. Key interaction states

| State | Presentation |
|---|---|
| Empty | centered icon + suggested prompts ("How do I improve retention?", "Write a Ship 30 essay…") |
| Loading / streaming | live token bubble grows in place; auto-scroll follows |
| Error | red-tinted bubble carrying the exact structured message from the API |
| Unsupported | neutral refusal text, no sources, suggestions of covered topics |
| Artifact ready | pane appears beside chat; meta badge shows type + word count |
| Provider misconfigured | error bubble: "ANTHROPIC_API_KEY is not configured…" with the fix |

## 4. Interaction patterns

- **Enter** sends; **Shift+Enter** inserts a newline; textarea auto-grows.
- Session click restores full history (Markdown re-rendered; artifacts re-openable per message).
- Delete requires confirmation (destructive action).
- Artifact button persists on historical messages → viewer reopens anytime.
- Hover reveals the delete control, keeping the sidebar visually quiet.

## 5. Trust UX

- Source chips are the *legend* for `(Source N)` numbering — any claim is auditable in two eye-movements.
- Refusal copy explains *why* ("the material doesn't support…") and offers covered topics, keeping users productive instead of stranded.
- The provider selector is always visible, so users always know *which model* answered.

## 6. Artifact viewer security (user-visible contract)

- HTML artifacts render in `<iframe sandbox="">`: scripts, forms, popups, and top-level navigation are **blocked**; static HTML/CSS layout is **allowed**.
- Markdown is parsed (marked.js) and sanitized (DOMPurify) before insertion.
- The pane header labels the artifact type and word count, so users always know what they are viewing.

## 7. Responsive behavior

- **≥ 1280 px:** three-region layout; artifact pane takes 50% beside the chat.
- **Narrow widths:** sidebar remains (primary navigation); artifact pane overlays content.
- **Known limitation:** below ~768 px the split becomes tight. Planned: full-screen artifact sheet on mobile.

## 8. Accessibility

- Icon-only controls carry `aria-label` + `title` (delete chat, close artifact).
- Semantic headings (`h1` app title, `h2` pane titles) and a labeled provider `<select>`.
- Focus-visible rings on all interactive elements; contrast-safe slate/indigo pairing.
- Keyboard-complete flow: Enter/Shift+Enter, tabbable session list, native confirm dialog for deletes.

## 9. Decisions & rationale

| Decision | Why |
|---|---|
| Vanilla JS + Tailwind CDN | zero build step → trivially reproducible for a fresh evaluator |
| marked.js + DOMPurify | battle-tested parsing/sanitization instead of hand-rolled converters |
| SSE streaming over WebSockets | native fetch streaming, no extra infra, works through Docker Compose |
| Sources as chips under the answer | readability first, auditability second (footnote pattern) |
| Deterministic small-talk guard | instant UX, zero GPU cost, removes a hallucination surface |
| Dark sidebar / light chat | clear visual separation of navigation vs. working surface |

## 10. Known limits & planned polish

- Clickable source chips → excerpt popovers (the data is already in the response).
- Mobile artifact sheet; virtualized history for very long sessions.
- Dark mode; per-session persisted provider preference.
- Replace Tailwind CDN with a build step for offline/production hardening.