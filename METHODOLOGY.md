# METHODOLOGY — content-scout

- **APEX-DEV version:** v0.1 (init-project v0.1)
- **Initialized:** 2026-07-17
- **Workflow:** `/start-story E#-S#` → implement → `/finish-story` → `/sprint-review` at sprint end. New scope via `/add-story`.

## Improvement log

Entries added when a session ends with "METHODOLOGY IMPROVEMENT: ..." notes; applied during /sprint-review.

- 2026-07-17 — init: The prescribed flat `/src` layout doesn't fit a two-service (FastAPI + Next.js) monorepo; used `backend/` + `frontend/` top-level instead. Consider adding a monorepo variant to the init-project template.
- 2026-07-28 — first-ever `/sprint-review` run on this project surfaced that 26 commits (2026-07-26→28, a full navigation/redesign overhaul, backfilled as epic E18) shipped with zero story IDs and zero BACKLOG.md/DONE.md/SPRINT.md entries — ad hoc chat requests had bypassed `/start-story`/`/finish-story` entirely for three days. Two changes made: (1) `sprint-review.md` v0.2→v0.3, step 1.5 now explicitly distinguishes an "untracked epic" (multi-day `feat:`/`redesign:` work with no story IDs) from a simple untracked-fix cluster, and surfaces it for an explicit user decision before continuing the review. (2) Added a "Story-tracking discipline" section to CLAUDE.md (project bootstrap, not a command file) instructing that ad hoc implementation requests either get a story ID via `/add-story` or an explicit end-of-session flag that the work needs backfilling — since CLAUDE.md is read every session regardless of which command (if any) is invoked, that's the only place a check like this actually fires for sessions that never touch the story machinery at all.
