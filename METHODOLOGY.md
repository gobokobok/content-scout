# METHODOLOGY — content-scout

- **APEX-DEV version:** v0.1 (init-project v0.1)
- **Initialized:** 2026-07-17
- **Workflow:** `/start-story E#-S#` → implement → `/finish-story` → `/sprint-review` at sprint end. New scope via `/add-story`.

## Improvement log

Entries added when a session ends with "METHODOLOGY IMPROVEMENT: ..." notes; applied during /sprint-review.

- 2026-07-17 — init: The prescribed flat `/src` layout doesn't fit a two-service (FastAPI + Next.js) monorepo; used `backend/` + `frontend/` top-level instead. Consider adding a monorepo variant to the init-project template.
