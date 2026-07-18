# DONE — content-scout

Completed stories land here, newest first. Format:

## [E#-S#] Title — YYYY-MM-DD
- What shipped
- Deviations from AC (if any)
- Handover notes for the next story

---

## [E5-S1] Results table — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `GET /runs/{run_id}/items?sort=&order=&page=` — server-side sorted, paginated endpoint (`backend/src/api/items.py`); 11 sortable fields, PAGE_SIZE=50, NULLs last in both directions
- `GET /projects/{project_id}/runs` — run list added to `backend/src/api/runs.py`
- `frontend/components/results-table.tsx` — TanStack Table v8 headless component; sticky account column + sticky header; horizontal scroll container (D16 mobile compliance)
- `frontend/app/(app)/projects/[id]/results/page.tsx` — full results page: run selector, sort/order state, pagination, "Запустить анализ" button
- `frontend/lib/api.ts` — `listRuns`, `listRunItems`, `ContentItemResponse`, `ItemSortField` added
- `frontend/package.json` — `@tanstack/react-table@^8.21.3` added (pre-approved in `docs/TECH_STACK.md`)
- Carousel/post views render as null in API → "—" in UI; sort treats as NULLs last via `.nulls_last()`
**Smoke test:** PASSED — Opened DEV results tab at `https://web-dev-99e3.up.railway.app/projects/082ae7c5-c40f-432d-80b0-c8b06a7ca015/results`; table rendered 7 content items with correct columns; clicked "Дата публикации" header — rows re-sorted newest-first with ▼ indicator; carousel row showed "—" for views; run selector showed 2 completed runs; "Запустить анализ" button present.
**Promoted to backlog:**
- None

---

## [E4-S2] Summarization in the run pipeline — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `AnalysisRun.progress_summarized` (new column, migration `c7e2f8a1b6d4`) tracks items summarized in the current phase.
- `src/services/usage.py:rollup_run_totals(session, run)` — sums all usage_events kinds into `total_cost_usd`, Claude-only kinds into `total_input_tokens`/`total_output_tokens`. Reusable pattern for E7-S1's usage rollups.
- `src/worker.py:process_run` now runs the real `summarizing` phase: batches pending (unsummarized) items through `summarize_run_items` in chunks of `Settings.summary_concurrency`, committing progress between batches; idempotent via a `summary IS NULL` filter, so a re-invocation skips already-summarized items.
- `src/api/runs.py:RunOut` and the frontend `RunResponse`/`run-dialog.tsx` now surface `progress_summarized`, `total_input_tokens`, `total_output_tokens`.
- ENV vars added: none.
**Smoke test:** PASSED — on DEV, through the real HTTP API (registered a fresh smoke-test user, created a project, added `natgeo`/`therock` as accounts, `POST /projects/{id}/runs` with a 3-day window, polled `GET /runs/{id}`): pending → scraping → done in ~3.5 min, `progress_summarized` reached 7/7 items, `total_input_tokens`=6151, `total_output_tokens`=683, `total_cost_usd`=$0.0796. Independently confirmed via direct DEV Postgres query that all 7 `content_items` got real non-empty Russian summaries (e.g. a Moana trailer, a London meet-and-greet clip) and that `usage_events` held the matching `apify_result`/`claude_input_tokens`/`claude_output_tokens` rows.
**Promoted to backlog:**
- (none)

---

## [E4-S1] Claude summarization service — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `src/services/summarizer.py:summarize_run_items(session, items, *, user_id, run_id)` is the only entry point — sets `ContentItem.summary` on each item in place and adds `claude_input_tokens`/`claude_output_tokens` usage_events rows; caller commits. Bounded concurrency via `Settings.summary_concurrency` (default 5).
- `FALLBACK_TEXT = "Описание недоступно"`; missing caption+image skip the API call entirely, an unfetchable image degrades to a text-only call, and 3 failed attempts (backoff) also fall back — a failed summary never raises.
- Prompt is docs/PROMPTS.md "Content summary (E4-S1)"; `SYSTEM_PROMPT` in the service mirrors it verbatim.
- `Settings` gained `anthropic_api_key`, `summary_model` (`claude-haiku-4-5-20251001`), `summary_concurrency` (5); reuses E3-S1's `claude_input_token_cost_usd`/`claude_output_token_cost_usd` for `unit_cost_usd`.
- E4-S2 wires this into the worker's `summarizing` phase (currently a pass-through) — call it with the run's content_items.
- ENV vars added: none new (`ANTHROPIC_API_KEY`/`SUMMARY_MODEL`/`SUMMARY_CONCURRENCY` already set on DEV).
**Smoke test:** PASSED — not yet reachable through the UI (worker wiring is E4-S2), so verified directly against DEV: ran `summarize_run_items` against a real content_item from the E3-S2 live run (a real @therock post about a Guinness World Record) using DEV's `ANTHROPIC_API_KEY` and DEV Postgres. Got back a genuine 2-sentence Russian summary describing the content (not its popularity), persisted to `content_items.summary`, with `claude_input_tokens`/`claude_output_tokens` usage_events rows recorded (1162 / 94 tokens) alongside the existing `apify_result` events for the same run.
**Promoted to backlog:**
- (none)

---

## [E3-S2] Apify Instagram integration and metrics — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `src/platforms/instagram.py:InstagramPlatform` — real Apify scraper (actor `apify/instagram-scraper`), 3× retry with backoff. `src/platforms/__init__.py:get_platform()` branches on `Settings.use_mock_platform` — DEV now runs the real platform (`USE_MOCK_PLATFORM=false`).
- `src/services/metrics.py` — SQL expression builders for `days_since_published`/`views_per_day`/`likes_per_day` (computed at read time per ARCHITECTURE.md); E5-S1's results query should use these directly.
- `src/worker.py:process_run` — per-account fetch failures no longer fail the run (`Account.status=failed` + `fail_reason`, run continues); writes one `apify_result` usage_events row per successful account fetch (quantity = items returned).
- `tests/fixtures/apify_ig_sample.json` — recorded-shape fixture (reel/post/carousel) for `test_instagram_platform.py`; extend rather than duplicate.
- ENV: `APIFY_IG_ACTOR_ID=apify/instagram-scraper` set on DEV (was genuinely missing); `APIFY_API_TOKEN`/`ANTHROPIC_API_KEY` were already set (ENV.md was stale, now corrected). `production` env vars unverified.
- Apify's actor emits an `{"error": ..., "errorDescription": ...}` placeholder item (not an exception) when a profile is blocked/private mid-run — `InstagramPlatform._fetch_once` now detects this and raises instead of normalizing it as a fake post; caught by the worker's per-account failure handling like any other account error.
**Smoke test:** PASSED — on DEV: ran analysis against 2 real public IG accounts (@natgeo, @therock), 3-day window, against the real Apify actor (not mock). 7 real content_items landed with real captions/likes/comments, view counts where Apify provided them, plausible published_at timestamps, and real IG CDN cover URLs; `apify_result` usage_events rows exist with correct quantities. Mid-run, Apify's scraper got blocked fetching part of @natgeo's posts and returned an `{"error": "no_items", ...}` placeholder instead of raising — the first code version silently stored that as a garbage content_item (fake row, all fields null). Caught this from the live data, fixed `InstagramPlatform` to detect the error shape and raise instead (now correctly marks the account failed with the real reason), added a regression test, deleted the one bad row from DEV, redeployed, re-verified clean.
**Promoted to backlog:**
- (none)

---

## [E3-S1] Run creation, cost estimate, worker skeleton — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `src/platforms/base.py:Platform`/`RawContentItem`; `src/platforms/__init__.py:get_platform(PlatformSlug)` currently maps IG to `MockPlatform` — E3-S2 swaps this to real `InstagramPlatform`, no other call site changes. `USE_MOCK_PLATFORM` env var has no effect yet (documented, starts mattering in E3-S2).
- `src/services/estimator.py:estimate_run`, `src/services/runs.py:resolve_target_accounts` (shared by API + worker), `src/services/queue.py:enqueue_run`.
- `src/worker.py:process_run(session, run)` (lifecycle core, testable) / `run_analysis(ctx, run_id)` (arq entrypoint) / `WorkerSettings`. **This deploy brings the `worker` Railway service up for the first time** (it was crash-looping since E1-S1 with no `worker.py`).
- `src/api/runs.py`: `POST /projects/{id}/runs/estimate`, `POST /projects/{id}/runs`, `GET /runs/{id}`.
- New migration `b2c1a4f9d7e3`: `analysis_runs.account_ids` (nullable `ARRAY(Uuid)`, NULL = whole list).
- Frontend: `app/(app)/projects/[id]/run-dialog.tsx` (estimate → confirm → 2s-poll progress); Конкуренты tab gained per-row/select-all checkboxes + "Запустить анализ" button.
- ENV vars added: none new to Railway; `Settings` gained `redis_url` + 5 estimator constants (local defaults).
**Smoke test:** PASSED — on DEV: opened a project's Конкуренты tab with accounts added, left all selected, clicked «Запустить анализ», saw the estimate (Apify units / Claude tokens / cost) for the full list × chosen duration, confirmed, and watched the dialog poll through Сбор публикаций → Формирование описаний → Готово within a few seconds (mock platform); confirmed the `worker` Railway service is up and healthy (previously crash-looping).
**Promoted to backlog:**
- (none)

---

## [E2-S2] Competitor list management (IG, max 50) — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `src/services/url_normalizer.py:normalize_instagram_input(raw) -> NormalizedAccount(handle, normalized_url)` — accepts `@handle`, bare `handle`, or any `instagram.com/<handle>` URL shape; rejects non-IG domains, non-profile paths (`/p/...`, `/reel/...`), malformed handles. Reuse for any future IG-URL input (bot sharing E8-S4, profile enrichment E2-S3).
- `src/services/projects.py:get_owned_project`/`ProjectNotFoundError` — workspace-ownership check extracted out of `api/projects.py` so every project-scoped router (accounts now; runs/results/shortlist later) shares one implementation.
- `src/api/accounts.py`: `GET/POST /projects/{id}/accounts` (bulk add, `{added, errors, total}`), `DELETE /projects/{id}/accounts/{account_id}`. IG `AccountList` is lazily created on first add.
- Frontend: `app/(app)/projects/[id]/competitors/page.tsx` is now the real tab (textarea bulk-paste, per-line Russian errors, "N / 50" counter, remove button) — no longer a placeholder. `lib/api.ts` gained account endpoints/types.
- ENV vars added: none.
**Smoke test:** PASSED — on DEV: pasted 5 lines (3 valid handles/URLs, 1 malformed, 1 duplicate of an already-added account) into a project's Конкуренты tab — 3 saved, the malformed line showed a Russian error, the duplicate was silently skipped, counter read the correct N / 50; removed one account and confirmed it disappeared from the list and the counter decremented.
**Promoted to backlog:**
- (none)

---

## [E2-S1] Project CRUD — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `src/services/workspace.py:get_user_workspace(session, user)` resolves a user's single personal workspace (one workspace per user per D6) — reuse this in every future project-scoped router instead of re-deriving membership.
- `src/api/projects.py`: `POST /projects`, `GET /projects` (`?include_archived=`), `GET/PATCH /projects/{id}`, `POST /projects/{id}/archive`; all workspace-scoped, 404 (`project_not_found`) for foreign/missing ids via the `_get_owned_project` helper — same pattern should be reused for E2-S2's accounts router.
- Frontend: `app/(app)/page.tsx` is now the project list (create + inline rename/archive); `app/(app)/projects/[id]/layout.tsx` is the shared project shell (back link, name, four-tab nav: Конкуренты/Результаты/Шорт-лист/История) — new tab content goes into the existing `competitors/`, `results/`, `shortlist/`, `history/` page files (currently "Скоро" placeholders), which inherit the shell automatically. E2-S2 replaces `competitors/page.tsx`.
- `lib/api.ts` gained `ProjectResponse` + `listProjects/createProject/getProject/renameProject/archiveProject`. New Russian strings under `Projects` and `ProjectShell` keys in `messages/ru.json`.
- ENV vars added: none.
**Smoke test:** PASSED — on DEV: created a project via «Создать проект», renamed it inline and confirmed the new name persisted in the list, opened it and confirmed all four tabs (Конкуренты/Результаты/Шорт-лист/История) render with placeholder text; archived it and confirmed it disappeared from the default list.
**Promoted to backlog:**
- (none)

---

## [E1-S3] Email+password auth and personal workspace — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- Auth stack: `src/auth/passwords.py` (bcrypt, imported directly — not via passlib, which is unmaintained and breaks under bcrypt≥4.1), `src/auth/tokens.py` (JWT create/decode), `src/auth/providers.py` (`AuthProvider` Protocol, `EmailPasswordProvider`, `create_user_with_workspace` helper), `src/auth/dependency.py` (`CurrentUser` FastAPI dependency).
- Routes: `POST /auth/register`, `POST /auth/login`, `GET /auth/me` in `src/api/auth.py`, mounted in `src/main.py`. Registration creates user + personal workspace + owner membership atomically (D6).
- Frontend: `lib/api.ts` typed client + `ApiError`, `lib/auth-context.tsx` (`AuthProvider`/`useAuth`, wraps root layout), `(auth)/login` + `(auth)/register` pages, `(app)/layout.tsx` guarded shell (redirects to `/login` when unauthenticated, shows email + logout) + `(app)/page.tsx` workspace placeholder.
- Root `app/page.tsx` was removed (Next route groups don't add URL segments — `(app)/page.tsx` now owns `/`).
- Future auth providers (Telegram D18, VK ID D4) implement `AuthProvider` and reuse `create_user_with_workspace` without touching call sites. Future protected pages go under `app/(app)/**` and inherit the guard for free.
- CI gained an explicit `mypy src` gate (was in CONVENTIONS.md but not enforced).
- ENV vars added: none.
**Smoke test:** PASSED — on DEV: registered a new user via the browser, landed in the authenticated Russian shell with email + «Выйти» shown; clicked logout, redirected to `/login`; logged back in with the same credentials, reached the shell again; cleared the token and confirmed `/` redirects unauthenticated users to `/login`; confirmed the login screen is fully usable at 375px width (D16).
**Promoted to backlog:**
- (none)

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
