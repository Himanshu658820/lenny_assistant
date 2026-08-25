# 01 — Stale image: new routes returned 404

**Context:** Added `/api/health/*` routes; browser showed `{"detail":"Not Found"}` while `/` and `/docs` worked.

**Diagnosis:** `docker compose logs` showed the app starting from an image built *before* the new files existed; compose only mounted `frontend/` and `data/`, so backend code was frozen at build time.

**Correction:** Mounted `./backend/app:/app/app` and switched to `uvicorn --reload`, making stale-image failures impossible during development; documented rebuild (`--build`) for dependency changes.

**Lesson:** Separate *code* changes (live mount) from *dependency* changes (rebuild) in Dockerized dev loops.