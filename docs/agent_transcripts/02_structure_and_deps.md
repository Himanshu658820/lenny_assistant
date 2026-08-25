# 02 — Misplaced packages and a missing dependency

**Failures:**
1. `ModuleNotFoundError: No module named 'app.db'` — files had been created under `app/api/db/` instead of `app/db/`.
2. `ModuleNotFoundError: No module named 'pgvector'` — requirement added but image not rebuilt.

**Corrections:** Moved files to correct packages; added `pgvector==0.3.0` to requirements and rebuilt.

**Lesson:** Volume mounts surface host structure exactly — import errors are usually a filesystem map, not a code bug. Dependencies require explicit rebuilds.