# 05 — SSE stream died and the UI hid it

**Failure:** User messages rendered; assistant bubble never appeared. Backend log:
`NameError: name 'json' is not defined` inside `chat_stream` — the generator crashed mid-stream after headers were sent.

**Secondary failure:** The frontend deleted the transient error bubble on final re-render, hiding the problem.

**Corrections:** Added `import json`; UI now always commits either the `done` payload or a visible error bubble.

**Lesson:** Streams fail after 200 OK — error UX must survive re-renders, and logs are the source of truth.