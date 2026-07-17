# DONE — content-scout

Completed stories land here, newest first. Format:

## [E#-S#] Title — YYYY-MM-DD
- What shipped
- Deviations from AC (if any)
- Handover notes for the next story

---

## [E1-S1] Monorepo scaffold, local env, CI, DEV deploy — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- Backend app factory: `backend/src/main.py` (`GET /health` → `{"status":"ok","env":...}`). Settings via `backend/src/config.py:get_settings()` — extend `Settings` here for future stories rather than adding a parallel config module.
- Backend pytest-asyncio/ruff/mypy config lives in `backend/pyproject.toml`.
- Frontend is a Next.js 15 App Router scaffold (TypeScript, Tailwind 4, next-intl) at `frontend/app/`; single-locale `ru` wired via `frontend/i18n/request.ts` (no routing middleware — add keys to `frontend/messages/ru.json`, one top-level key per page, e.g. `HomePage`).
- Root layout (`frontend/app/layout.tsx`) sets base light/dark background+text on `<body>`; new pages can build on top of that.
- `.claude/launch.json` added for Claude Code's own dev-server preview (not part of the shipped app).
- No new ENV vars.
- Deviation: `backend/Dockerfile` (listed in the story's file plan) was skipped — Railway is already configured for the `nixpacks` builder, so a Dockerfile would be unused. See BACKLOG.md Changelog for E1-S1 for full rationale and the frontend dependency version bumps made to clear `npm audit` findings.
**Smoke test:** PASSED — `pytest` green, `GET /health` hit directly against a live `uvicorn` instance returned `{"status":"ok","env":"local"}`; frontend `build`/`lint`/`typecheck` all green and the Russian placeholder was visually confirmed in-browser at both light/dark themes and 375px width. DEV push-based smoke test (`curl <dev-api>/health`, open DEV frontend URL) confirmed via the CI/CD run triggered by this story's commit.
**Promoted to backlog:**
- (none)
