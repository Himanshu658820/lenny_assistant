# 04 — Grounding quality iteration (precision vs recall)

**Observed failures (manual eval):**
1. "hii" produced a full AI-growth answer with sources.
2. "my name is himanshu saini" answered about the *previous* topic (Elon Musk).
3. "According to Eric Ries…" refused despite `eric ries 2` being indexed.

**Root causes:** threshold too permissive for greetings; no small-talk guard; model context bleed; chunk embeddings lacked document identity.

**Corrections:**
- Deterministic small-talk guard skill (regex; instant, zero GPU).
- System prompt: answer only the latest question; one consistent stance.
- Metadata-augmented embeddings (`Episode: {title}\nSection: {heading}\n…`).
- Knobs: `TOP_K=8`, `RELEVANCE_THRESHOLD=0.40` (env-tunable, no code change).

**Result:** greetings instant; refusals honest and consistent; name-based queries grounded (verified: Duolingo, Caitlin Kalinowski answers).

**Lesson:** Grounding is a product feature you tune, not a flag you flip.