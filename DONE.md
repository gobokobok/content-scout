# DONE — content-scout

Completed stories land here, newest first. Format:

## [E#-S#] Title — YYYY-MM-DD
- What shipped
- Deviations from AC (if any)
- Handover notes for the next story

---

## [E1-S2] Database schema and migrations — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- Full 10-table MVP schema live on DEV (alembic revision 3a1974cc55cf): users, workspaces, workspace_members, projects, account_lists, accounts, analysis_runs, content_items, shortlist_items, usage_events.
- Import everything from `src.models`; `Base.metadata` carries naming conventions. Enums are varchar+CHECK (`native_enum=False`) so adding values is a cheap migration; `usage_events.kind` is a free string by design (D26).
- DB plumbing: `src/db.py` (`get_engine`, `get_sessionmaker`, `get_session` FastAPI dependency); `Settings.database_url_async` rewrites Railway's `postgres://` to asyncpg.
- DB-enforced rules: duration_days 1–7 CHECK; unique (account_list_id, normalized_url); one list per platform; partial-unique *active* shortlist entries (soft-delete via removed_at); `account_list_cap` trigger blocks the 51st account (raises check_violation — app-level friendly check still required in E2-S2).
- Test infra: `session` fixture (savepoint rollback per test) + model factories in `tests/conftest.py`. Locally there is no Docker — tests/autogenerate run against a `content_scout_test` DB on the DEV Railway Postgres (slow, ~2 min); CI uses its own Postgres and is the authoritative gate.
- **Migrations now auto-apply on deploy**: api start command is `alembic upgrade head && uvicorn ...` in both envs.
- Ops incident fixed in passing: dashboard secret-entry had wiped the non-secret service variables on api/worker/web in both envs (api crashlooped on localhost DB fallback); all restored via CLI. Railway's raw editor replaces the entire variable set — don't use it for single additions.
- ENV vars added: none.
**Smoke test:** PASSED — DEV api healthy after deploy (migrations ran on boot); direct DB check confirmed all 10 tables + alembic_version at 3a1974cc55cf + cap trigger present.
**Promoted to backlog:**
- (none)

## [E1-S1] Monorepo scaffold, local env, CI, DEV deploy — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- Backend app factory: `backend/src/main.py` (`GET /health` → `{"status":"ok","env":...}`). Settings via `backend/src/config.py:get_settings()` — extend `Settings` here for future stories rather than adding a parallel config module.
- Backend pytest-asyncio/ruff/mypy config lives in `backend/pyproject.toml`.
- Frontend is a Next.js 15 App Router scaffold (TypeScript, Tailwind 4, next-intl) at `frontend/app/`; single-locale `ru` wired via `frontend/i18n/request.ts` (no routing middleware — add keys to `frontend/messages/ru.json`, one top-level key per page, e.g. `HomePage`).
- Root layout (`frontend/app/layout.tsx`) sets base light/dark background+text on `<body>`; new pages can build on top of that.
- `.claude/launch.json` added for Claude Code's own dev-server preview (not part of the shipped app).
- No new app-level ENV vars. Railway-side (not app code): `RAILPACK_START_CMD` is now required per-service on `api`/`worker` in the dev environment (`uvicorn src.main:app --host 0.0.0.0 --port $PORT` / `arq src.worker.WorkerSettings`) — Railway's Railpack builder can't auto-detect a start command when `main.py` is nested under `src/`. **Still needed:** the same two variables on `api`/`worker` in the `production` environment before the first `v*` tag is pushed, or `cd.yml` will hit the identical "No start command detected" build failure.
- Deviation: `backend/Dockerfile` (listed in the story's file plan) was skipped — Railway is already configured for the `nixpacks` builder, so a Dockerfile would be unused. See BACKLOG.md Changelog for E1-S1 for full rationale and the frontend dependency version bumps made to clear `npm audit` findings.
- Also fixed (in the same push sequence): `.github/workflows/ci.yml`/`cd.yml` were calling `npx railway up`, which resolves to an unrelated npm package, not Railway's CLI — both now use `npx @railway/cli`. Then found the `RAILWAY_TOKEN_DEV`/`RAILWAY_TOKEN_PROD` secrets were GitHub **Environment** secrets (on Environments `DEV`/`PROD`), which need the job to declare `environment: <name>` to see them — added that too. Finally hit the `RAILPACK_START_CMD` gap above, which you fixed directly in the Railway dashboard.
**Smoke test:** PASSED — local: `pytest` green, `GET /health` hit directly against a live `uvicorn` instance returned `{"status":"ok","env":"local"}`; frontend `build`/`lint`/`typecheck` all green, Russian placeholder visually confirmed in-browser at light/dark themes and 375px width. DEV (real push-triggered deploy): `curl https://api-dev-8d6e.up.railway.app/health` → `{"status":"ok","env":"dev"}`; `https://web-dev-99e3.up.railway.app/` → 200 with the Russian placeholder.
**Promoted to backlog:**
- (none — the production `RAILPACK_START_CMD` gap is a pre-launch ops checklist item, not new story-shaped work; tracked in this entry's Handover above and in ENV.md.)
