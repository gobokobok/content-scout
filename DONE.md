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
- Also fixed (in the same push sequence): `.github/workflows/ci.yml`/`cd.yml` were calling `npx railway up`, which resolves to an unrelated npm package, not Railway's CLI. Both now use `npx @railway/cli`. Then found the `RAILWAY_TOKEN_DEV`/`RAILWAY_TOKEN_PROD` secrets you added were GitHub **Environment** secrets (on Environments `DEV`/`PROD`), which need the job to declare `environment: <name>` to see them — added that too.
**Smoke test:** DEFERRED — local smoke test PASSED (`pytest` green, `GET /health` hit directly against a live `uvicorn` instance returned `{"status":"ok","env":"local"}`; frontend `build`/`lint`/`typecheck` all green, Russian placeholder visually confirmed in-browser at light/dark themes and 375px width). DEV push-based smoke test is PARTIAL: `deploy-dev` now succeeds and `https://web-dev-99e3.up.railway.app/` serves the live Russian placeholder (frontend half PASSED); `https://api-dev-8d6e.up.railway.app/health` still 404s with Railway's own "Application not found" after 6+ minutes, which doesn't look like a slow build (the frontend, deployed in the same run, was already live). Needs a look at the `api` service's Railway dashboard build/deploy logs — no Railway dashboard/CLI credentials available from this session to dig further.
**Promoted to backlog:**
- (none)
