# Manual UI Test Plan

Run against http://localhost:8000 after ingestion. ✅/❌ each row.

## Chat & grounding
- [ ] Ask "How did Duolingo reignite user growth?" → streamed answer, ≥1 source chip, specific facts.
- [ ] Ask "What lessons does Caitlin Kalinowski's Tesla experience teach about vertical integration?" → cites caitlin kalinowski.
- [ ] Follow-up in same session ("Which tactic mattered most early?") → resolves context, no topic bleed.
- [ ] Ask "What does Lenny's podcast say about meme stocks?" → honest refusal, no invented facts.
- [ ] Type "hii" → instant friendly guard, no sources, no GPU wait.
- [ ] Type "my name is <name>" → personalized greeting.

## Sessions
- [ ] New Chat resets context; sidebar lists sessions with titles.
- [ ] Reload page → open a session → full history restored.
- [ ] Hover session → trash icon → delete removes it (confirm dialog).

## Skills & artifacts
- [ ] "Write a Ship 30 for 30 essay about activation vs vanity metrics" → artifact pane opens; hook, headings, bullets, bold, "The takeaway"; word count 1000–1500.
- [ ] "Create an HTML one-pager about growth loops" → renders in viewer.
- [ ] Security: HTML artifact with `<script>alert(1)</script>` + form → renders inert (no alert).
- [ ] Markdown artifact renders styled (headings/bullets), sanitized.

## Provider toggle & resilience
- [ ] Switch to Anthropic without key → instant readable error bubble (structured 503).
- [ ] Switch back to Ollama → works.
- [ ] `docker compose stop ollama` → chat shows readable error; `start` → recovers.
- [ ] `/api/health/ready` shows database+ollama ok; with db stopped → 503.

## UX states
- [ ] Empty state visible on new chat; typing indicator/streaming visible; error state styled; Enter sends, Shift+Enter newlines; layout usable at 1280px and mobile width.