# 03 — Real-world data breaks naive schemas

**Failure 1:** `psycopg.errors.StringDataRightTruncation: value too long for character varying(300)` —
Markdown headings containing full URLs exceeded the `heading` column.

**Correction:** `documents.title` and `chunks.heading` changed to `TEXT`; volume wiped and re-ingested.

**Failure 2:** Ollama container: `model "nomic-embed-text" not found` — host models invisible to the container.

**Correction:** Mounted `${USERPROFILE}/.ollama:/root/.ollama` so the container reuses host models; documented `ollama pull` fallback for fresh machines.

**Lesson:** Schema limits and environment isolation are the first things real corpora attack.