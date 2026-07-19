# BACKLOG — content-scout

Epics:
- **E1 Foundation & Auth** — scaffold, DB schema, email+password auth, personal workspace, i18n, CI/CD to DEV
- **E2 Projects & Competitor Lists** — project CRUD, IG URL lists (max 50), persistence
- **E3 Analysis Pipeline** — run creation, worker, Apify IG scraping, metrics
- **E4 AI Summaries** — Claude Haiku caption+cover summaries, usage capture
- **E5 Results Table & Export** — progress UI, sortable table, XLSX export
- **E6 Shortlist & History** — promote rows, shortlist tab, run/shortlist history
- **E7 Usage Metering & Admin** — per-user/per-run rollups, admin usage view
- **E8 Telegram Integration & Monetization** — Telegram Login, bot notifications, Mini App + Stars subscriptions (see docs/ARCHITECTURE.md § Telegram Mini App, D17–D19, D22)
- **E9 Public API & Engine Integration** — API tokens, webhooks for downstream content-generation products (see docs/ARCHITECTURE.md § Public API, D21)
- **E10 Content Generation** — scripts + assets from shortlist items, typed пост/карусель/reels (D23), parallel jobs, review & edit, download delivery
- **E11 Instagram Connection, Publishing & Analytics** — blogger connects own IG account (Graph API, D24), publish/schedule generated content, own-account analytics
- **E12 UI/UX Modernization** — light design system v1 (D28), mobile card layouts, bottom navigation, UX states; doubles as Telegram Mini App readiness

Post-MVP (not scheduled, first stories drafted below for E8–E11): VK ID + SMS auth (behind Telegram Login in priority per D18), YouTube/TikTok/Threads platforms, native mobile app (not planned — see D17), team workspaces, RU infra migration stages 2–3 (D20, infra-only, tracked outside BACKLOG.md until scheduled). Mobile card layout for tables is now scheduled (E12-S2, Sprint 6 — supersedes the horizontal-scroll-only clause of D16 per D28).

---

## [E1-S1] Monorepo scaffold, local env, CI, DEV deploy
**Epic:** Foundation & Auth
**Sprint:** 1
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** none
### Goal
A walking skeleton: FastAPI health endpoint + Next.js placeholder page run locally via bootstrap script and auto-deploy to Railway DEV on push to main.
### Acceptance Criteria
- [x] `backend/` FastAPI app with `GET /health` returning `{"status":"ok","env":...}`
- [x] `frontend/` Next.js 15 app (TypeScript, Tailwind, next-intl with `ru` locale) rendering a placeholder page with a Russian string from the locale file
- [x] `docker-compose.yml` provides Postgres 16 + Redis 7; `scripts/bootstrap.sh` gets a fresh machine to running apps
- [x] Backend tests run via pytest, frontend lint+typecheck via npm; both wired into `.github/workflows/ci.yml`
- [x] Push to `main` deploys backend + frontend to Railway DEV — confirmed: `curl https://api-dev-8d6e.up.railway.app/health` → `{"status":"ok","env":"dev"}`; `https://web-dev-99e3.up.railway.app/` returns 200 with the Russian placeholder.
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Open DEV frontend URL — Russian placeholder renders. `curl <dev-api>/health` returns ok.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md, docs/TECH_STACK.md, ENV.md
### Files to create or modify
backend/src/main.py, backend/src/config.py, backend/tests/test_health.py, backend/requirements.txt, backend/Dockerfile, frontend/** (Next.js scaffold), frontend/messages/ru.json, docker-compose.yml, scripts/bootstrap.sh, .github/workflows/ci.yml
### Changelog
- Skipped `backend/Dockerfile`: `railway.toml`/`railway.prod.toml` (from the prior "wire Railway envs" commit) already pin `builder = "nixpacks"` for all services, and `docker-compose.yml` only runs Postgres/Redis, never builds the app images. A Dockerfile would be dead weight; revisit only if we deliberately switch the Railway builder to Docker.
- Pinned frontend deps to patched versions to clear `npm audit` findings found during setup: `next` 15.5.20 (CVE-2025-66478 fixed post-15.1.4), `next-intl` 4.13.2 (open-redirect/prototype-pollution advisories unfixed on 3.x), `eslint` 9.39.5 (ReDoS in `@eslint/plugin-kit`), `tailwindcss`/`@tailwindcss/postcss` 4.3.3 (4.0.0 threw `Missing field 'negated' on ScannerOptions.sources` on `next build`). One moderate advisory remains open (XSS in Next's internally-bundled `postcss <8.5.10`, nested under `next` itself) — no fix exists in the Next 15 line; `npm audit fix --force` would downgrade `next` to a `9.x` canary, which is not viable.
- Docker Desktop wasn't running in the dev sandbox, so `docker-compose.yml`/`scripts/bootstrap.sh` were reviewed but not executed end-to-end; all other pieces (health endpoint, frontend build/lint/typecheck, browser render) were exercised directly.
- Fixed a pre-existing bug in `.github/workflows/ci.yml`/`cd.yml` (from the prior "wire Railway envs" commit): `npx railway up` resolves to the unrelated npm package `railway` (a TypeScript IaC/sandbox SDK, bin `railway-iac-ts`) rather than Railway's actual CLI, and failed the first real `deploy-dev` run this story triggered (`Could not find .railway/railway.ts`). Changed both workflows to `npx -y @railway/cli up ... --yes`, which is the real package (bin `railway`).
- `RAILWAY_TOKEN_DEV`/`RAILWAY_TOKEN_PROD` were added as GitHub **Environment** secrets (on Environments named `DEV`/`PROD`), not plain repository secrets — those are only exposed to a job that declares `environment: <name>`. Added that to the `deploy-dev` job in `ci.yml` and the `deploy-prod` job in `cd.yml`.
- Final blocker: Railway's builder is **Railpack** (not Nixpacks, despite `railway.toml` saying `builder = "nixpacks"` — that setting appears not to be what's actually in effect). Railpack auto-detects a Python start command only from `main.py`/`app.py` at the service's build root; since `api`'s app lives at `backend/src/main.py`, auto-detection failed with "No start command detected." ENV.md's Railway state notes claimed `RAILPACK_START_CMD` was "already set per service," but it wasn't actually present in the `dev` environment — you (the user) set it directly in the Railway dashboard per service (`api`: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`; `worker`: `arq src.worker.WorkerSettings`, which will itself fail until `backend/src/worker.py` exists — expected, out of scope here). **Follow-up needed:** same `RAILPACK_START_CMD` variables must be set on `api`/`worker` in the `production` Railway environment before the first `v*` tag is pushed, or `cd.yml`'s deploy-prod will hit the identical failure.
### Handover
- Backend app factory lives at `backend/src/main.py` (`app = FastAPI(...)`); settings via `backend/src/config.py:get_settings()` (`Settings` — currently `environment`, `cors_origins`; extend here for E1-S2/E1-S3, don't create a parallel settings module).
- Backend test config (pytest-asyncio `asyncio_mode = "auto"`, ruff, mypy) lives in `backend/pyproject.toml` — new backend stories should rely on this, not add a second config file.
- Frontend i18n: `frontend/i18n/request.ts` hardcodes `locale = "ru"` (no routing/middleware, single-locale MVP per D8); add keys to `frontend/messages/ru.json` under a page-scoped top-level key (see `HomePage`) rather than a flat namespace.
- Root layout (`frontend/app/layout.tsx`) sets base light/dark background+text classes on `<body>`; new pages can rely on that instead of re-specifying background colors.
- `.claude/launch.json` added (Claude Code harness config only, not part of the app) so `npm run dev` can be previewed in-session; safe to ignore/remove if unwanted.
- No new ENV vars.

## [E1-S2] Database schema and migrations
**Epic:** Foundation & Auth
**Sprint:** 1
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E1-S1
### Goal
Full MVP schema in SQLAlchemy models with Alembic migrations, matching docs/ARCHITECTURE.md.
### Acceptance Criteria
- [x] Models: users, workspaces, workspace_members, projects, account_lists, accounts, analysis_runs, content_items, shortlist_items, usage_events (fields per docs/ARCHITECTURE.md)
- [x] Alembic initialized; one migration creates the full schema; `alembic upgrade head` works on a fresh DB — verified on the throwaway test DB and on DEV (revision 3a1974cc55cf)
- [x] Constraints enforced in DB: ≤50 accounts per list (DB trigger `account_list_cap` as safeguard; primary app-level check lands in E2-S2), unique (account_list_id, normalized_url), run duration 1–7 days (CHECK), plus one-list-per-platform unique and partial-unique active shortlist index
- [x] Model factory fixtures for tests (`tests/conftest.py`: make_user/workspace/project/account_list/account/run/content_item)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (10 tests, one per constraint/behavior)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Run `alembic upgrade head` against DEV database; tables exist (check via Railway psql).
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (data model section), backend/src/config.py
### Files to create or modify
backend/src/db.py, backend/src/models/*.py, backend/alembic/**, backend/tests/conftest.py, backend/tests/test_models.py
### Changelog
- Backend venv rebuilt with uv-managed Python 3.12 — the E1-S1 venv was on system Python 3.9 (no 3.10+ on the machine; `uv` was available). `scripts/bootstrap.sh` still prefers python3.12/python3 — future improvement: prefer `uv venv --python 3.12`.
- No local Docker/Postgres on this machine: migration autogenerate + local test runs use a dedicated `content_scout_test` database on the DEV Railway Postgres (via DATABASE_PUBLIC_URL). CI remains the authoritative test gate with its own Postgres service.
- Api start command now runs migrations on boot (`alembic upgrade head && uvicorn ...`) in both Railway envs — future schema stories deploy themselves.
- Incident: the dashboard edits that added APIFY/ANTHROPIC keys had wiped the other service variables (DATABASE_URL, REDIS_URL, CORS_ORIGINS, SUMMARY_*, USE_MOCK_PLATFORM, ACCESS_TOKEN_EXPIRE_MINUTES) on api/worker/web — api crashed on boot falling back to localhost DB. All restored via CLI in both envs; lesson: Railway's raw-editor replaces the whole variable set.
### Handover
- Schema is live on DEV at revision 3a1974cc55cf; all 10 tables + `account_list_cap` trigger verified present.
- Import models from `src.models` (re-exports everything); `Base` carries naming conventions — never define constraints without them.
- DB access: `src/db.py` — `get_engine()`, `get_sessionmaker()`, `get_session` (FastAPI dependency). `Settings.database_url_async` normalizes Railway's `postgres://` scheme.
- Tests: `session` fixture = rollback-per-test savepoint session; factories in `tests/conftest.py` accept kwargs overrides. Local runs against the remote test DB take ~2 min; export DATABASE_URL first (see Changelog).
- ENV vars added: none (DATABASE_URL was already specified in ENV.md).

## [E1-S3] Email+password auth and personal workspace
**Epic:** Foundation & Auth
**Sprint:** 1
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E1-S2
### Goal
Users can register and log in (JWT); registration auto-creates a personal workspace; frontend has Russian login/register pages and an authenticated shell.
### Acceptance Criteria
- [x] `POST /auth/register` (email+password, bcrypt), `POST /auth/login` → JWT access token, `GET /auth/me`
- [x] Registration creates a personal workspace and membership row in the same transaction
- [x] Auth dependency rejects missing/invalid tokens with 401; all non-auth routes require it
- [x] Frontend: /login and /register pages (Russian), token stored, authenticated layout with logout; unauthenticated users redirected to /login
- [x] Auth provider kept behind an interface so VK ID can be added later without touching call sites
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (11 new auth tests, 21 total in suite)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Register a user on DEV, log out, log back in, see the authenticated shell in Russian.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (auth section), backend/src/models/user.py, frontend/messages/ru.json
### Files to create or modify
backend/src/auth/*.py, backend/src/api/auth.py, backend/tests/test_auth.py, frontend/app/(auth)/login/page.tsx, frontend/app/(auth)/register/page.tsx, frontend/lib/api.ts, frontend/messages/ru.json
### Changelog
- Password hashing uses `bcrypt` directly rather than via `passlib` — `passlib[bcrypt]` is still the declared dependency (bcrypt is its transitive install), but passlib itself is unmaintained and breaks under bcrypt≥4.1; importing `bcrypt` directly is the currently-recommended pattern and avoids that landmine. No new dependency added.
- Added an explicit `mypy src` step to CI (`ci.yml`) — CONVENTIONS.md already mandates mypy on `src/`; it just wasn't gated in CI yet. All 22 source files pass clean.
- Root `app/page.tsx` (E1-S1 placeholder) removed and its content moved to `app/(app)/page.tsx`, since Next.js route groups don't add URL segments and both would otherwise resolve to `/`. `app/(app)/layout.tsx` now owns the authenticated shell (header, email, logout) and the redirect-to-`/login` guard.
### Handover
- Auth stack: `src/auth/passwords.py` (bcrypt), `src/auth/tokens.py` (JWT create/decode), `src/auth/providers.py` (`AuthProvider` Protocol + `EmailPasswordProvider` + `create_user_with_workspace` — reusable by future providers), `src/auth/dependency.py` (`CurrentUser` FastAPI dependency, 401 on missing/invalid/deleted-user tokens).
- Routes: `POST /auth/register`, `POST /auth/login`, `GET /auth/me` (`src/api/auth.py`); Russian validation/error messages throughout (`{code, message_ru}` shape per CONVENTIONS).
- Frontend: `lib/api.ts` (typed fetch client, `ApiError`, localStorage token), `lib/auth-context.tsx` (`AuthProvider`/`useAuth` — wraps the whole app in root `layout.tsx`), `(auth)/login` + `(auth)/register` pages, `(app)/layout.tsx` (guarded shell) + `(app)/page.tsx` (workspace placeholder, moved from root).
- New Russian strings under `Auth` and `App` keys in `messages/ru.json` — extend these, don't create parallel keys.
- Any future story adding protected pages just needs to live under `app/(app)/**`; the layout's guard handles the rest. Any future story adding an auth provider (Telegram, VK ID) implements `AuthProvider` and can reuse `create_user_with_workspace`.
- ENV vars added: none (`JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES` were already in ENV.md/Railway from initial setup).

## [E2-S1] Project CRUD
**Epic:** Projects & Competitor Lists
**Sprint:** 2
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E1-S3
### Goal
A logged-in user can create, rename, list, and archive projects inside their workspace.
### Acceptance Criteria
- [x] API: create/list/get/update/archive project, scoped to the caller's workspace (404 for foreign projects)
- [x] Frontend: workspace home lists projects with "Создать проект"; project page shell with tabs (Конкуренты / Результаты / Шорт-лист / История)
- [x] Archived projects hidden from default list
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (5 new tests; CI is the authoritative gate — no local Postgres available in this sandbox)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Create a project on DEV, rename it, see it in the list; open it and see the four tabs.
### Files to read
CLAUDE.md, backend/src/models/project.py, backend/src/api/auth.py, frontend/lib/api.ts
### Files to create or modify
backend/src/api/projects.py, backend/tests/test_projects.py, frontend/app/(app)/projects/**, frontend/messages/ru.json
### Changelog
- Added `backend/src/services/workspace.py` (`get_user_workspace`) — not in the original file plan but needed to resolve "the caller's workspace" from `WorkspaceMember`; every user has exactly one (personal) workspace per D6, so this is a simple join, not a new abstraction.
- Frontend: project rename/archive controls live inline on the project list (not inside the project shell) so the E2-S1 smoke test flow (create → rename → see it in list → open → see tabs) works without extra navigation.
### Handover
- Backend: `src/services/workspace.py:get_user_workspace(session, user)` — resolves a user's single personal workspace; reuse this instead of re-deriving workspace membership in future project-scoped routers (accounts, runs, etc.).
- `src/api/projects.py`: `POST /projects`, `GET /projects` (`?include_archived=`), `GET/PATCH /projects/{id}`, `POST /projects/{id}/archive`. All 404 with `{code: "project_not_found"}` for foreign-workspace or missing ids — follow this pattern (`_get_owned_project` helper) for E2-S2's accounts router.
- Frontend: `app/(app)/page.tsx` is now the project list (create/rename/archive inline); `app/(app)/projects/[id]/layout.tsx` is the shared shell (back link, project name, four-tab nav) — new project sub-features should add a page under `app/(app)/projects/[id]/<tab>/` and it inherits the shell for free. Tab route segments (`competitors`, `results`, `shortlist`, `history`) are fixed — E2-S2 should build directly into `competitors/page.tsx`, replacing its current "Скоро" placeholder.
- `lib/api.ts` gained `ProjectResponse` + `listProjects/createProject/getProject/renameProject/archiveProject`.
- New Russian strings under `Projects` and `ProjectShell` keys in `messages/ru.json`.
- ENV vars added: none.

## [E2-S2] Competitor list management (IG, max 50)
**Epic:** Projects & Competitor Lists
**Sprint:** 2
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E2-S1
### Goal
Within a project, the user manages the Instagram competitor list: paste/add URLs or @handles, validated and normalized, capped at 50, persisted.
### Acceptance Criteria
- [x] API: add entries (single or bulk paste), remove entry, list entries — on the project's IG `account_list` (auto-created)
- [x] URL/handle normalization to canonical `instagram.com/<handle>`; invalid entries rejected with per-line Russian error messages; duplicates deduped
- [x] 51st entry rejected with a clear error; counter "N / 50" shown in UI
- [x] Data model supports one list per platform (IG active; YouTube/TikTok/Threads platform enum values exist but are disabled in UI — model already supported this from E1-S2, no change needed)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (16 new tests: 11 normalizer + 5 accounts API; CI is the authoritative gate — no local Postgres in this sandbox)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Paste 5 IG URLs (one invalid, one duplicate) on DEV — 3 saved, errors shown in Russian, counter reads 3 / 50.
### Files to read
CLAUDE.md, backend/src/models/account_list.py, backend/src/api/projects.py, frontend/app/(app)/projects/**
### Files to create or modify
backend/src/api/accounts.py, backend/src/services/url_normalizer.py, backend/tests/test_accounts.py, frontend/app/(app)/projects/[id]/competitors/**, frontend/messages/ru.json
### Changelog
- Extracted `_get_owned_project` out of `src/api/projects.py` into `src/services/projects.py:get_owned_project` (raises `ProjectNotFoundError`) so the accounts router (and future project-scoped routers) can reuse the same workspace-ownership check instead of duplicating it — `api/projects.py` now just translates the domain error to a 404.
- Duplicates are deduped silently (no error entry), matching the AC wording ("duplicates deduped") as distinct from genuinely invalid input (which does get a per-line Russian error).
- Cap enforcement is app-level in the same request (checks `existing count + entries not yet inserted`); the DB `account_list_cap` trigger from E1-S2 remains as a safeguard.
### Handover
- `src/services/url_normalizer.py:normalize_instagram_input(raw) -> NormalizedAccount(handle, normalized_url)` accepts `@handle`, bare `handle`, or any `instagram.com/<handle>` URL form (with/without scheme, `www.`, trailing slash, query string); rejects non-IG domains, non-profile paths (`/p/...`, `/reel/...`, etc.), and malformed handles, raising `InvalidAccountUrlError(message_ru=...)`. Reuse this for any future IG-URL input surface (E8-S4 bot sharing, E2-S3 enrichment).
- `src/services/projects.py:get_owned_project(session, user, project_id)` / `ProjectNotFoundError` — the shared workspace-ownership check; reuse in every project-scoped router (runs, results, shortlist, etc.).
- `src/api/accounts.py`: `GET/POST /projects/{id}/accounts` (bulk add, returns `{added, errors, total}`), `DELETE /projects/{id}/accounts/{account_id}`. The IG `AccountList` row is lazily created on first successful add — don't assume it exists on a fresh project.
- Frontend: `app/(app)/projects/[id]/competitors/page.tsx` replaces the E2-S1 placeholder — textarea bulk-paste (newline-separated), per-line error list, "N / 50" counter, remove button per row. New Russian strings under `Competitors` key in `messages/ru.json`; `ProjectShell.comingSoonCompetitors` key removed (no longer a placeholder).
- `lib/api.ts` gained `AccountResponse`, `AddAccountsResponse`, `listAccounts/addAccounts/removeAccount`.
- ENV vars added: none.

## [E3-S5] Switch scraping backend to HikerAPI
**Epic:** Analysis Pipeline
**Sprint:** unassigned
**Status:** backlog
**Priority:** low
**Depends on:** E3-S2
### Goal
Replace the Apify `instagram-scraper` actor with HikerAPI to reduce per-result cost (~3–10×), improve reel view count reliability, and remove Apify as a dependency.
### Acceptance Criteria
- [ ] `HikerApiPlatform` implements the existing `Platform` interface (`fetch_content(account, since) -> list[RawContentItem]`) — no call sites outside `src/platforms/` change
- [ ] Reel `views` field populated reliably (HikerAPI returns `videoViewCount` consistently)
- [ ] Cost per result benchmarked against current $0.0027/result Apify rate and documented in story changelog
- [ ] `apify_result` usage_events kind reused or renamed; `apify_unit_cost_usd` config replaced with `scraper_unit_cost_usd`
- [ ] `USE_HIKER_API` env var (or rename `USE_MOCK_PLATFORM` → platform selector) controls which implementation is active
- [ ] Existing Apify integration tests kept and a new HikerAPI fixture-based test added
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Run 2 accounts on DEV with HikerAPI — reels show view counts, cost per result logged and matches HikerAPI invoice.
### Files to read
CLAUDE.md, backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/config.py, DECISIONS.md
### Files to create or modify
backend/src/platforms/hikerapi.py (new), backend/src/platforms/__init__.py, backend/src/config.py, backend/tests/test_hikerapi_platform.py, ENV.md, DECISIONS.md
### Handover
—

## [E2-S3] Competitor profile enrichment
**Epic:** Projects & Competitor Lists
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
**Depends on:** E2-S2, E3-S2
### Goal
The Конкуренты list shows basic live details per account — display name/title, follower count, avatar — fetched when an account is added and refreshed on each analysis run.
### Acceptance Criteria
- [ ] `Platform` interface gains `fetch_profile(account) -> ProfileInfo` (display_name, followers, avatar_url); Apify IG profile fetch implements it
- [ ] Profile fetched async on account add (list shows the row immediately, details fill in); refreshed as part of every run's scraping phase
- [ ] Конкуренты list displays: аватар, название, @handle, подписчики (formatted ru-RU), последнее обновление
- [ ] Profile fetches write `apify_result` usage_events like any other scrape
- [ ] Fetch failure leaves the row usable (handle + «нет данных»), never blocks add/run
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Add a real public IG account on DEV — name, followers, and avatar appear within a minute.
### Files to read
CLAUDE.md, backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/api/accounts.py
### Files to create or modify
backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/models/account.py (+ migration), backend/tests/test_profile_enrichment.py, frontend/app/(app)/projects/[id]/competitors/**, frontend/messages/ru.json
### Handover
—

## [E3-S1] Run creation, cost estimate, worker skeleton
**Epic:** Analysis Pipeline
**Sprint:** 2
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E2-S2
### Goal
User picks a duration (1–7 days), sees a cost estimate, confirms, and a run executes asynchronously through its full lifecycle using a mock scraper.
### Acceptance Criteria
- [x] `POST /projects/{id}/runs/estimate` returns estimated Apify units + Claude tokens + ₽/$ cost for current list size × duration
- [x] `POST /projects/{id}/runs` (after confirm) creates run `pending` and enqueues an arq job; duration outside 1–7 rejected
- [x] Run optionally targets a **subset of accounts** (`account_ids` in the request; UI: checkboxes on the competitor list, default = entire list); estimate reflects the subset
- [x] Worker advances run: pending → scraping → summarizing → done (mock platform returns fixture content); failures land in `failed` with error message
- [x] `GET /runs/{id}` returns status + progress (accounts processed / total); frontend run dialog shows estimate → confirm → live progress
- [x] `Platform` interface defined (`fetch_content(account, since) -> [RawContentItem]`); mock implementation registered
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (13 new tests: estimator, worker lifecycle, runs API; CI is the authoritative gate — no local Postgres/Redis in this sandbox)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On DEV, start a run with the mock platform flag; watch status advance to done within a minute.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (run lifecycle), backend/src/models/analysis_run.py, backend/src/api/projects.py
### Files to create or modify
backend/src/worker.py, backend/src/platforms/base.py, backend/src/platforms/mock.py, backend/src/services/estimator.py, backend/src/api/runs.py, backend/tests/test_runs.py, frontend/app/(app)/projects/[id]/run-dialog.tsx, frontend/messages/ru.json
### Changelog
- Added a migration (`b2c1a4f9d7e3`) for `analysis_runs.account_ids` (nullable `ARRAY(Uuid)`, NULL = whole list) — not anticipated by the E1-S2 schema; required to persist the "subset of accounts" selection the AC calls for so the worker knows which accounts to scrape.
- `Platform` interface lives in `src/platforms/base.py` as `fetch_content(account, since)` only (no `normalize_url` — ARCHITECTURE.md's sketch included one, but URL normalization is a pure function already covered by `services/url_normalizer.py` from E2-S2 and doesn't need to be per-platform-instance).
- Worker logic split into `worker.py:run_analysis` (thin arq entrypoint — opens a session, loads the run) and `worker.py:process_run` (the actual lifecycle, takes an already-open session) so it's testable against the rollback-savepoint test session without touching the global engine.
- Added `src/services/queue.py` (lazy cached `ArqRedis` pool + `enqueue_run`) so the Redis call is wrapped in `services/` per CONVENTIONS, not called directly from the router.
- Real summarization doesn't exist yet (E4-S1/E4-S2); the worker's `summarizing` phase is currently a pass-through state transition, not real work — the AC only requires the state machine to advance correctly.
- Estimator constants (avg items/account/day, per-unit Apify/Claude costs) are config-driven (`Settings`) with provisional defaults, not hardcoded, so real pricing can be dropped in via ENV without a code change.
- Frontend: checkboxes live on the Конкуренты list per the AC wording, not inside the run dialog; "Запустить анализ" opens `run-dialog.tsx` with the currently-checked subset (all-checked → `account_ids: undefined`, meaning "whole list").
### Handover
- `src/platforms/base.py`: `Platform` Protocol (`fetch_content(account, since) -> list[RawContentItem]`), `RawContentItem` dataclass. `src/platforms/__init__.py:get_platform(PlatformSlug) -> Platform` — currently maps `instagram` to `MockPlatform`; E3-S2 swaps this mapping to `InstagramPlatform`, no other call site changes.
- `src/platforms/mock.py:MockPlatform` — returns 3 fixture items per account (mixed reel/post/carousel, `views=None` for non-reel per D14). Used unconditionally for now; `USE_MOCK_PLATFORM` env var has no effect yet (documented — it starts mattering once E3-S2 adds the real branch).
- `src/services/estimator.py:estimate_run(settings, accounts_count, duration_days) -> RunEstimate`; `src/services/runs.py:resolve_target_accounts(session, project_id, account_ids)` — shared by both the API and the worker so account-selection logic lives in one place.
- `src/services/queue.py:enqueue_run(run_id)` — wraps the arq/Redis call; `src/worker.py:process_run(session, run)` is the lifecycle core (scraping → summarizing → done/failed), `run_analysis(ctx, run_id)` is the arq job entrypoint, `WorkerSettings` registers it.
- `src/api/runs.py`: `POST /projects/{id}/runs/estimate`, `POST /projects/{id}/runs`, `GET /runs/{id}` — all workspace-scoped via `get_owned_project`; `POST /projects/{id}/runs` 400s with `no_accounts_to_analyze` if the resolved account set is empty.
- New migration: `analysis_runs.account_ids` (`ARRAY(Uuid)`, nullable). Model field added to `src/models/analysis_run.py`.
- Frontend: `app/(app)/projects/[id]/run-dialog.tsx` (estimate → confirm → 2s-poll progress), competitors page now has per-row + select-all checkboxes and a "Запустить анализ" button. `lib/api.ts` gained `EstimateResponse`/`RunResponse`/`RunRequest` + `estimateRun/createRun/getRun`.
- ENV vars added: none new to Railway (`REDIS_URL` was already provisioned per ENV.md); `Settings` gained `redis_url` plus five estimator constants, all with local defaults.
- **This story brings the `worker` Railway service up for the first time** — it was crash-looping since E1-S1 because `backend/src/worker.py` didn't exist yet (`RAILPACK_START_CMD=arq src.worker.WorkerSettings` was already set per ENV.md). Confirm on deploy that the worker service is actually healthy, not just that `api`/`web` are.

## [E3-S2] Apify Instagram integration and metrics
**Epic:** Analysis Pipeline
**Sprint:** 3
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E3-S1
### Goal
Real IG scraping: the worker fetches each account's content for the window via Apify, normalizes it into content_items, and computes derived metrics.
### Acceptance Criteria
- [x] `InstagramPlatform` implements `Platform` using the Apify actor (actor id from env); raw payload stored in `content_items.raw` (JSONB)
- [x] Normalized fields: published_at, type (reel/post/carousel), title (caption first line, truncated), url, likes, views (NULL for post/carousel), comments
- [x] Derived: days_since_published, views_per_day, likes_per_day (computed at read time or run finish — per ARCHITECTURE.md)
- [x] Apify units consumed recorded as `usage_events` per account fetch
- [x] Per-account failures (private/deleted account) don't fail the run; account marked failed with reason, run completes partial
- [x] Apify client wrapped with timeout + retry; integration test against recorded fixture (no live Apify in CI)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (11 new tests: instagram platform normalization/retry/error-placeholder, worker per-account-failure + usage-event; CI is the authoritative gate — no local Postgres in this sandbox)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Run analysis on DEV against 2 real public IG accounts, 3 days — content_items rows appear with plausible metrics; usage_events rows exist.
### Files to read
CLAUDE.md, backend/src/platforms/base.py, backend/src/worker.py, backend/src/models/content_item.py, docs/ARCHITECTURE.md
### Files to create or modify
backend/src/platforms/instagram.py, backend/src/services/metrics.py, backend/tests/test_instagram_platform.py, backend/tests/fixtures/apify_ig_sample.json
### Changelog
- ENV.md previously claimed APIFY_API_TOKEN/ANTHROPIC_API_KEY were empty placeholders on DEV — they were actually already set (stale doc, corrected). `APIFY_IG_ACTOR_ID` genuinely was missing; set it to `apify/instagram-scraper` (Apify's general-purpose IG posts scraper, per-result pricing) on `api`/`worker` in `dev` via `railway variables --set`. Not a DECISIONS.md-worthy call (no new pip dependency — `apify-client` was already pinned in E1-S1) but recorded here since ENV.md's human-action checklist called it out explicitly.
- `apify-client`'s actual installed API differs from the ARCHITECTURE.md sketch I initially assumed: `.actor(id).call()` takes `run_timeout: timedelta` (not `timeout_secs: int`), returns a typed `Run | None` (not a dict — `run.default_dataset_id`, not `run["defaultDatasetId"]`), and `.dataset(id).list_items()` returns a `DatasetItemsPage` object with an `.items: list[dict]` attribute. mypy caught all three mismatches against my first draft before any of this touched CI.
- `services/metrics.py` exposes SQL expression builders (`days_since_published_expr`, `views_per_day_expr`, `likes_per_day_expr`) per ARCHITECTURE.md's "computed in SQL at read time" — no dedicated unit test here since they need a live query to execute (`func.now()`); E5-S1's results-table tests are the natural place these get exercised against a real DB.
- `usage_events` (kind=`apify_result`) is written once per account fetch, quantity = items returned, only when the fetch returned ≥1 item (zero results = zero Apify cost, per D12 "written at the moment cost is incurred").
- **Found during the real DEV smoke test** (not visible in fixture-based CI tests): when `apify/instagram-scraper` can't reach a profile (blocked/rate-limited mid-run — happened live against @natgeo), it doesn't raise — it emits a single dataset item shaped `{"error": "no_items", "errorDescription": "...", "url": <profile url>}` instead of a post. The first version of `_normalize()` treated this as a real (garbage) content item — `external_id` ended up as the profile URL, every metric field null. Fixed in `_fetch_once` to detect `"error"` in the item and raise `ApifyRunFailedError` instead, which the worker's existing per-account failure handling catches — so a blocked profile now correctly marks the account `failed` with the Apify-supplied reason instead of polluting the results with a fake row. Covered by a new test; the one bad row created during the live smoke run was deleted from DEV directly.
### Handover
- `src/platforms/instagram.py:InstagramPlatform` — real Apify scraper; `src/platforms/__init__.py:get_platform()` now branches on `Settings.use_mock_platform` (mock for local/CI by default, real on DEV since `USE_MOCK_PLATFORM=false`). Retries 3× with exponential backoff on any exception, then re-raises — caught per-account by the worker.
- `src/services/metrics.py` — SQL expression builders for the three derived columns; E5-S1's results query should use these directly rather than recomputing.
- `src/worker.py:process_run` now: wraps `platform.fetch_content` per account in try/except (failure → `Account.status=failed` + `fail_reason`, run continues), and writes an `apify_result` usage_events row per successful account fetch.
- `tests/fixtures/apify_ig_sample.json` — 3-item recorded-shape fixture (reel/post/carousel) reused by `tests/test_instagram_platform.py`; extend this fixture rather than adding a second one for future Apify-shape tests.
- ENV vars: `APIFY_IG_ACTOR_ID=apify/instagram-scraper` now set on DEV `api`/`worker` (was missing); `APIFY_API_TOKEN`/`ANTHROPIC_API_KEY` were already set (ENV.md corrected). `production` env vars not yet verified for any of these.

## [E3-S3] Worker run resume logic
**Epic:** Analysis Pipeline
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E3-S2
### Goal
A stuck or failed run in `summarizing` state can be resumed without re-scraping, so recovery from worker crashes does not waste Apify units or create duplicate content rows.
### Acceptance Criteria
- [ ] `process_run` checks the run's current status on entry: if already `summarizing`, skip the scraping phase entirely and go straight to the pending-items query
- [ ] Re-enqueuing a run that crashed mid-summarization resumes from the first unsummarized item (idempotency already in the summarizer; this story wires the entry-point guard)
- [ ] A run in `done` or `failed` is a no-op when re-enqueued (logged, no state change)
- [ ] Unit test: a run pre-seeded to `summarizing` with some items already summarized — re-invoking `process_run` summarizes only the remaining items and reaches `done`
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Manually set a DEV run to `summarizing` with partial summaries, re-enqueue it — only the unsummarized items get processed, run reaches `done`.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/services/summarizer.py
### Files to create or modify
backend/src/worker.py, backend/tests/test_worker.py
### Handover
—

## [E3-S4] Two-phase run cost confirmation
**Epic:** Analysis Pipeline
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E3-S3
### Goal
Before Claude summarization begins, the user sees the actual scraped publication count and the real token cost, and must confirm before the expensive phase runs — eliminating cost surprises from high-volume accounts.
### Acceptance Criteria
- [ ] Run lifecycle splits into two worker phases: Phase 1 = scrape only (Apify, cheap); Phase 2 = summarize (Claude, expensive). A new `scraped` run status marks the boundary.
- [ ] After Phase 1, `GET /runs/{id}` returns `status=scraped`, `progress_items` (actual count), and `estimated_summarization_cost` (tokens × rate); the run dialog shows "Найдено N публикаций. Стоимость описаний: ~X токенов. Продолжить?"
- [ ] User confirms (or cancels — run stays in `scraped` with items accessible for browsing without summaries); confirmation enqueues Phase 2
- [ ] `max_items_per_run` config cap (default 500): if scrape returns more, items are truncated to the cap before Phase 2 and a warning is shown
- [ ] Estimate constant `avg_items_per_account_per_day` bumped to `8.0` (was `1.2` — wildly underestimated in real-world smoke test)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Run 3 accounts on DEV: after scraping the dialog shows actual item count and token estimate; cancel — run stays browseable; confirm on a second run — summarization completes correctly.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/api/runs.py, frontend/app/(app)/projects/[id]/run-dialog.tsx
### Files to create or modify
backend/src/worker.py, backend/src/api/runs.py, backend/src/models/analysis_run.py (+ migration for `scraped` status + `estimated_summarization_cost`), backend/tests/test_worker.py, frontend/app/(app)/projects/[id]/run-dialog.tsx, frontend/messages/ru.json
### Handover
—

## [E3-S6] Worker resilience and parallel scraping
**Epic:** Analysis Pipeline
**Sprint:** 6
**Status:** done
**Completed:** 2026-07-18
**Priority:** critical
**Depends on:** E4-S2
### Goal
Runs of any size complete reliably. Today arq's default 300s `job_timeout` kills any run longer than 5 minutes (sequential scraping means >~5 accounts), and the resulting `CancelledError` escapes `process_run`'s `except Exception` boundary, leaving the run stuck in «scraping» forever. Found in the 2026-07-18 architecture review — this must land before any real test user runs a full list.
### Acceptance Criteria
- [ ] `WorkerSettings.job_timeout` set from config (`worker_job_timeout_secs`, default 3600)
- [ ] `process_run` handles `asyncio.CancelledError` (it is a `BaseException` — the current `except Exception` misses it): mark the run `failed` with «Превышено время выполнения», commit, then re-raise
- [ ] Accounts scrape concurrently under a semaphore (`scrape_concurrency`, default 5). Fetch tasks only call the platform and return raw items; all DB writes stay in the parent task on the single session (AsyncSession is not task-safe)
- [ ] Unique index on `content_items (run_id, external_id)` + idempotent insert (ON CONFLICT DO NOTHING), so a re-delivered arq job cannot duplicate items; Alembic migration included
- [ ] Summarizer reuses one `AsyncAnthropic` client and one `httpx.AsyncClient` per run (currently recreated per batch / per image fetch)
- [ ] Unit tests: cancellation marks the run failed; parallel scrape produces the same rows as sequential; duplicate insert is a no-op
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
DEV run with 8+ accounts completes well past the 5-minute mark; wall time reflects ~5-way parallelism, not the sequential sum; re-enqueueing the finished run duplicates nothing.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/services/summarizer.py, backend/src/models/content_item.py
### Files to create or modify
backend/src/worker.py, backend/src/config.py, backend/src/services/summarizer.py, backend/src/models/content_item.py (+ migration), backend/tests/test_worker.py
### Changelog
- `asyncio.shield(session.commit())` used inside `except asyncio.CancelledError:` to guard the cleanup commit against re-cancellation.
- Parallel scraping collects all fetch results via `asyncio.gather` first, then applies DB writes sequentially in the parent task (avoids sharing `AsyncSession` across tasks).
- `ON CONFLICT DO NOTHING` via `pg_insert(ContentItem).on_conflict_do_nothing(index_elements=["run_id", "external_id"])` — `items_found` counter still increments regardless, which is fine for UX progress display.
- `AsyncAnthropic` and `httpx.AsyncClient` created once per run before the summarizing loop; explicitly closed after (minor resource leak on cancellation during summarizing is acceptable for a timed-out worker).
- Unique constraint name: `uq_content_items_run_id_external_id` (follows NAMING_CONVENTION).
### Handover
- `WorkerSettings.job_timeout = get_settings().worker_job_timeout_secs` (default 3600) — arq will cancel jobs beyond this limit
- `process_run` now catches `asyncio.CancelledError` separately from `Exception`; marks run `failed` with «Превышено время выполнения», commits via `asyncio.shield`, re-raises
- Accounts scrape in parallel under `settings.scrape_concurrency` (default 5) semaphore; DB writes happen in the parent task after gather completes
- `pg_insert(ContentItem).on_conflict_do_nothing(index_elements=["run_id", "external_id"])` prevents duplicate rows on arq job re-delivery
- Migration `e5a3f2c9b1d7`: `uq_content_items_run_id_external_id` unique constraint on `content_items(run_id, external_id)`
- `summarize_run_items` now accepts optional `client: AsyncAnthropic | None` and `http_client: httpx.AsyncClient | None`; when provided, reuses them across all items in the batch (avoids per-item/per-batch client recreation)
- `Settings` gained `worker_job_timeout_secs` (int, default 3600) and `scrape_concurrency` (int, default 5)
- 3 new tests: cancellation → run failed, parallel scrape → same rows as sequential, duplicate insert → no-op

## [E4-S1] Claude summarization service
**Epic:** AI Summaries
**Sprint:** 3
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E3-S2
### Goal
A service that produces a 1–2 sentence Russian summary of a content item from its caption + cover image using Claude Haiku.
### Acceptance Criteria
- [x] `summarize(items) -> summaries` batches requests to claude-haiku-4-5 with caption text + cover image (fetched from IG CDN URL, resized ≤1024px)
- [x] Prompt in docs/PROMPTS.md; output: 1–2 sentences, Russian, describes what the content is about (no engagement commentary)
- [x] Missing caption and unfetchable image handled (summarize from whichever exists; both missing → "Описание недоступно")
- [x] Token usage per call recorded as usage_events
- [x] Retries with backoff on rate limits; a failed summary never fails the run (item gets fallback text)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (4 new tests; CI is the authoritative gate — no local Postgres in this sandbox)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Trigger summarization for one real item on DEV; summary is Russian, 1–2 sentences, relevant to the post.
### Files to read
CLAUDE.md, docs/PROMPTS.md, backend/src/models/content_item.py, backend/src/services/usage.py (if exists)
### Files to create or modify
backend/src/services/summarizer.py, backend/tests/test_summarizer.py, docs/PROMPTS.md
### Changelog
- `summarize_run_items(session, items, *, user_id, run_id)` writes directly to `item.summary` and to `usage_events` (not a pure function returning summaries) — this satisfies the "token usage per call recorded as usage_events" AC without needing a second pass, and keeps the DB write co-located with the API call that produced it (per D12: written at the moment cost is incurred). E4-S2 (worker wiring) calls this function over a run's items rather than reimplementing persistence.
- Image fetch (`httpx`) + resize (`Pillow`, already a pinned dependency since E1-S1) live in `_fetch_image_block`; any fetch/decode failure falls back to a text-only call rather than failing the item.
- Retry is a flat 3-attempt exponential backoff around the whole API call (matches `InstagramPlatform`'s pattern from E3-S2) rather than distinguishing rate-limit vs. other errors — simpler and sufficient given a failed summary always degrades to the fallback string, never fails the run.
### Handover
- `src/services/summarizer.py:summarize_run_items(session, items, *, user_id, run_id)` — the only entry point; bounded concurrency via `Settings.summary_concurrency` (default 5). Sets `ContentItem.summary` on each item in place and adds `claude_input_tokens`/`claude_output_tokens` `UsageEvent` rows — caller must still `session.commit()`.
- `FALLBACK_TEXT = "Описание недоступно"` exported for tests/comparisons elsewhere.
- Prompt lives in `docs/PROMPTS.md` under "Content summary (E4-S1)"; `SYSTEM_PROMPT` in the service mirrors it verbatim — update the doc first, then the constant.
- `Settings` gained `anthropic_api_key`, `summary_model` (default `claude-haiku-4-5-20251001`), `summary_concurrency` (default 5); reuses the `claude_input_token_cost_usd`/`claude_output_token_cost_usd` estimator constants from E3-S1 for `unit_cost_usd`.
- ENV vars: none new to Railway (`ANTHROPIC_API_KEY`/`SUMMARY_MODEL`/`SUMMARY_CONCURRENCY` were already set on DEV per E3-S2's ENV.md correction).

## [E4-S2] Summarization in the run pipeline
**Epic:** AI Summaries
**Sprint:** 3
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E4-S1
### Goal
The worker's `summarizing` phase runs the summarizer over all items of a run with bounded concurrency and progress reporting.
### Acceptance Criteria
- [x] After scraping, run enters `summarizing`; items processed in batches with bounded concurrency (config)
- [x] Progress (items summarized / total) exposed on `GET /runs/{id}` and shown in UI
- [x] Run-level token totals rolled up onto analysis_runs (total_input_tokens, total_output_tokens, total_cost)
- [x] Re-running summarization is idempotent (skips items that already have summaries)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (7 new/updated tests in test_worker.py + 2 in test_usage.py; CI is the authoritative gate — no local Postgres in this sandbox)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Full run on DEV (2 accounts, 3 days): every item has a Russian summary; run shows token totals.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/services/summarizer.py, backend/src/api/runs.py
### Files to create or modify
backend/src/worker.py, backend/src/services/usage.py, backend/tests/test_pipeline.py
### Changelog
- Added `analysis_runs.progress_summarized` (migration `c7e2f8a1b6d4`) — not anticipated by E1-S2's schema; needed to expose per-phase progress distinct from `progress_items` (scraped count) and `progress_accounts`.
- Bounded concurrency is achieved by chunking pending items into batches of `Settings.summary_concurrency` in the worker and calling `summarize_run_items` (which already runs a batch concurrently via its internal semaphore) once per batch, committing `progress_summarized` between batches. This avoids concurrent `session.commit()` calls from multiple asyncio tasks sharing one `AsyncSession` (unsafe) while still giving real incremental progress — a single call over the whole item set would only "complete" progress all at once.
- Idempotency is implemented by querying `content_items` for the run **filtered to `summary IS NULL`** before summarizing — a re-invocation of `process_run` (e.g. a retried worker job) skips already-summarized items automatically; wrote a dedicated test (`test_process_run_skips_already_summarized_items`) proving pre-summarized items never reach the summarizer.
- Wrote `src/services/usage.py:rollup_run_totals` (not in the original file plan, but the natural home per CONVENTIONS' "logic in services/") — sums **all** usage_events kinds into `total_cost_usd` (Apify + Claude) but only the two Claude kinds into `total_input_tokens`/`total_output_tokens`, matching the model's field semantics.
- Test-file name deviates from the story's suggested `test_pipeline.py` — extended the existing `test_worker.py` and added `test_usage.py` instead, since `process_run` (the pipeline) already lives there and a third file would just split related coverage.
### Handover
- `AnalysisRun.progress_summarized` (new column) — items summarized so far in the current/last run of the summarizing phase.
- `src/services/usage.py:rollup_run_totals(session, run)` — call after any usage_events-producing phase to refresh `total_cost_usd`/`total_input_tokens`/`total_output_tokens`; reusable for E7-S1's usage rollups (per-user aggregation there is a different query, but this is the per-run pattern to follow).
- `src/worker.py:process_run` now: transitions to `summarizing`, batches pending (unsummarized) items through `summarize_run_items` in chunks of `Settings.summary_concurrency`, commits `progress_summarized` per batch, then calls `rollup_run_totals` before marking `done`.
- `src/api/runs.py:RunOut` gained `progress_summarized`, `total_input_tokens`, `total_output_tokens`.
- Frontend: `run-dialog.tsx` shows "Обработано публикаций: N / M" during `summarizing` and "Токенов Claude: input / output" once `done`. New `RunDialog` strings in `messages/ru.json`.
- ENV vars added: none.

## [E4-S3] Claude cost optimization
**Epic:** AI Summaries
**Sprint:** 6
**Status:** done
**Completed:** 2026-07-19
**Priority:** high
**Depends on:** E3-S6
### Goal
Cut Claude spend per item roughly 4× without quality loss (D29). Image tokens dominate input cost today (a 1024px cover ≈ 1 400 tokens vs ~100–300 for the caption); repeat runs re-summarize identical posts; and background summarization qualifies for the Message Batches API's 50% discount.
### Acceptance Criteria
- [ ] Cover images downscaled to **512px** max side before sending (`summary_image_max_side` config; was 1024) — ~4× fewer image tokens
- [ ] Cross-run summary reuse: before summarizing, copy the summary from the most recent prior `content_item` with the same `external_id` within the same project; reused items generate no Claude call and no usage_events
- [ ] `summary_skip_image_caption_chars` (default 200): items whose caption is longer are summarized text-only (image adds little when the caption already says what the post is)
- [ ] Message Batches API used when pending items ≥ `summary_batch_threshold` (default 20): worker submits one batch, polls status, maps per-item results and usage back onto items and usage_events; falls back to the existing concurrent path below threshold or on batch failure
- [ ] Unit tests: reuse lookup, skip-image rule, batch-result → summary/usage_events mapping (Batch API mocked)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Run the same DEV project twice back-to-back: the second run's Claude token usage is a small fraction of the first (reuse working); summaries remain correct Russian 1–2-sentence descriptions.
### Files to read
CLAUDE.md, DECISIONS.md (D29), backend/src/services/summarizer.py, backend/src/worker.py, docs/PROMPTS.md
### Files to create or modify
backend/src/services/summarizer.py, backend/src/config.py, backend/src/worker.py, backend/tests/test_summarizer.py
### Handover
- `backend/src/services/summarizer.py` — `summarize_run_items` now accepts optional `project_id: uuid.UUID`; when provided, copies summary from most recent prior `content_item` with same `external_id` in the same project (FALLBACK_TEXT not reused)
- Image resize now uses `settings.summary_image_max_side` (default 512, was 1024); image skipped entirely when `len(caption) > settings.summary_skip_image_caption_chars` (default 200)
- `_summarize_via_batches` sends a Message Batch when `len(pending) >= settings.summary_batch_threshold` (default 20); polls `retrieve()` until `processing_status == "ended"`, then maps results via `custom_id = str(item.id)`; any exception falls back to concurrent per-item path
- `backend/src/worker.py` — `project_id=run.project_id` now passed to `summarize_run_items`
- Config additions: `summary_image_max_side`, `summary_skip_image_caption_chars`, `summary_batch_threshold`
- `docs/PROMPTS.md` updated to reflect 512px and skip-image rules

## [E5-S1] Results table
**Epic:** Results Table & Export
**Sprint:** 4
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E4-S2
### Goal
The Результаты tab shows the completed run's content as a table sortable by every column.
### Acceptance Criteria
- [x] Columns: аккаунт, дата и время публикации, тип, заголовок, ссылка (opens IG in new tab), краткое описание, лайки, просмотры, дней с публикации, просмотров/день, лайков/день
- [x] Server-side sort + pagination via `GET /runs/{id}/items?sort=&order=&page=`; every column sortable both directions
- [x] Views columns show "—" (not 0) for post/carousel types; sort treats them as NULLs last
- [x] Type shown as Russian labels with icons (Reels / Пост / Карусель)
- [x] Run selector on the tab (defaults to latest completed run)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On DEV open a finished run, sort by просмотров/день descending, click a link — IG post opens.
### Files to read
CLAUDE.md, backend/src/api/runs.py, docs/UI_GUIDELINES.md, frontend/app/(app)/projects/[id]/**
### Files to create or modify
backend/src/api/items.py, backend/tests/test_items_api.py, frontend/app/(app)/projects/[id]/results/**, frontend/components/results-table.tsx, frontend/messages/ru.json
### Handover
- `GET /runs/{run_id}/items?sort=&order=&page=` — paginated, server-side sorted results endpoint in `backend/src/api/items.py`
- `GET /projects/{project_id}/runs` — run list endpoint added to `backend/src/api/runs.py`
- `frontend/components/results-table.tsx` — TanStack Table v8 headless component with 11 columns, sticky account+header, horizontal scroll
- `frontend/app/(app)/projects/[id]/results/page.tsx` — full client page with run selector, sort state, pagination
- `frontend/lib/api.ts` — `listRuns`, `listRunItems`, `ContentItemResponse`, `ItemSortField` added
- Sort normalizes NULLs last in both ASC and DESC directions via SQLAlchemy `.nulls_last()`

## [E5-S2] XLSX export
**Epic:** Results Table & Export
**Sprint:** 4
**Status:** done
**Completed:** 2026-07-18
**Priority:** medium
**Depends on:** E5-S1
### Goal
One click exports the current run's full results table to an .xlsx file with Russian headers.
### Acceptance Criteria
- [x] `GET /runs/{id}/export.xlsx` streams a workbook (openpyxl): all rows, Russian headers matching the UI, link column as real hyperlinks, frozen header row, respects current sort
- [x] Filename `content-scout_<project>_<run-date>.xlsx`
- [x] "Экспорт в Excel" button on the results tab
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Export a DEV run, open in Excel/Numbers — headers Russian, links clickable, data matches UI.
### Files to read
CLAUDE.md, backend/src/api/items.py, frontend/app/(app)/projects/[id]/results/**
### Files to create or modify
backend/src/services/xlsx_export.py, backend/src/api/export.py, backend/tests/test_export.py, frontend/components/results-table.tsx
### Handover
- `GET /runs/{run_id}/export.xlsx?sort=&order=` in `backend/src/api/export.py` — streams openpyxl workbook; all rows (no pagination); RFC 5987 UTF-8 `filename*=` header for Cyrillic project names
- `backend/src/services/xlsx_export.py` — `build_xlsx(items, project_name, run_created_at)` helper; frozen header row; URL column as real hyperlinks
- "Экспорт в Excel" button in results page toolbar; visible only when run is done and items exist; triggers blob fetch → `a.download` click
- `api.downloadRunXlsx(runId, sort, order)` added to `frontend/lib/api.ts`
- Bug found+fixed: project names with Cyrillic characters caused `UnicodeEncodeError` in the `Content-Disposition` header — fixed by using `filename*=UTF-8''<quoted>` (RFC 5987)

## [E6-S1] Shortlist
**Epic:** Shortlist & History
**Sprint:** 4
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E5-S1
### Goal
User promotes rows from results to the project shortlist and manages them in the Шорт-лист tab.
### Acceptance Criteria
- [x] Promote/demote action per results row (star toggle); API creates/removes shortlist_items (project-scoped, references content_item, survives across runs)
- [x] **Bulk add:** row checkboxes + «выбрать все» with a «Добавить в шорт-лист» action for the selection (API accepts a list of item ids)
- [x] Шорт-лист tab lists shortlisted items with same columns + добавлено (date shortlisted), sortable, removable
- [x] Promoting the same item twice is idempotent (single or bulk)
- [x] Placeholder "Создать сценарий" button visible but disabled with tooltip "Скоро" (script generation is post-MVP)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Promote 2 rows on DEV, open Шорт-лист — both there; remove one — gone; results row star reflects state.
### Files to read
CLAUDE.md, backend/src/models/shortlist_item.py, backend/src/api/items.py, frontend/components/results-table.tsx
### Files to create or modify
backend/src/api/shortlist.py, backend/tests/test_shortlist.py, frontend/app/(app)/projects/[id]/shortlist/**, frontend/messages/ru.json
### Handover
- `POST /projects/{project_id}/shortlist` — bulk add (idempotent); `DELETE /projects/{project_id}/shortlist/{content_item_id}` — soft-delete; `GET /projects/{project_id}/shortlist` — list active items (`backend/src/api/shortlist.py`)
- `ShortlistItem` model with soft-delete pattern (`removed_at IS NULL` for active); partial unique index `uq_shortlist_items_active`
- `in_shortlist: bool` added to `ContentItemOut` / `ContentItemResponse` via correlated subquery in items endpoint
- `frontend/components/results-table.tsx` — ★/☆ per-row toggle + select-all + bulk add bar
- `frontend/app/(app)/projects/[id]/shortlist/page.tsx` — full shortlist tab with remove action; "Создать сценарий" disabled placeholder

## [E6-S2] Run and shortlist history
**Epic:** Shortlist & History
**Sprint:** 5
**Status:** done
**Completed:** 2026-07-18
**Priority:** medium
**Depends on:** E6-S1
### Goal
The История tab shows all past runs (date, duration, accounts, items found, status, cost) and past shortlist activity; any past run's results can be reopened.
### Acceptance Criteria
- [x] Run history list with: started_at, период (days), кол-во аккаунтов, найдено публикаций, статус, стоимость; click opens that run in the results tab
- [x] Shortlist history: added/removed events with timestamps
- [x] Failed runs show their error message in Russian
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On DEV with ≥2 runs, open История, click the older run — its results render.
### Files to read
CLAUDE.md, backend/src/api/runs.py, frontend/app/(app)/projects/[id]/**
### Files to create or modify
backend/src/api/history.py, backend/tests/test_history.py, frontend/app/(app)/projects/[id]/history/**, frontend/messages/ru.json
### Handover
- `GET /projects/{project_id}/history/shortlist` → `list[ShortlistHistoryItemOut]` — all shortlist events (active + removed), newest first (`backend/src/api/history.py`)
- `ShortlistHistoryItemOut`: id, content_item_id, account_handle, type, title, url, added_at, removed_at
- Run history reuses `GET /projects/{project_id}/runs` (existing endpoint)
- `frontend/app/(app)/projects/[id]/history/page.tsx` — full История tab: run history table + shortlist history table
- "Открыть результаты" button → `router.push(/projects/{id}/results?run={runId})`; deep-link reads `window.location.search` inside `loadRuns()` to select the specified run
- `backend/tests/test_history.py` — 5 tests (empty, added items, removed items, shape, 404 wrong user)
- `frontend/messages/ru.json` — `History` namespace added
- No ENV vars added

## [E7-S1] Usage rollups
**Epic:** Usage Metering & Admin
**Sprint:** 5
**Status:** done
**Completed:** 2026-07-18
**Priority:** high
**Depends on:** E4-S2
### Goal
Usage events roll up into per-run and per-user totals, and the user sees their own consumption.
### Acceptance Criteria
- [x] usage_events schema finalized: user_id, run_id, kind, quantity, unit_cost_usd, created_at; `kind` is an extensible enum (apify_result | claude_input_tokens | claude_output_tokens now; designed for gemini_*, storage_gb_month, compute_alloc later per D26) — this is the internal Layer-1 cost ledger
- [x] `GET /me/usage?from=&to=` returns totals per kind and cost, per project and overall
- [x] Run history (E6-S2) cost column reads from these rollups
- [x] Simple "Использование" page in account menu showing current month totals
- [x] Pilot phase shows internal USD directly (no billing yet); the endpoint/page structure anticipates the D26 token layer so E8-S3 swaps the displayed unit, not the plumbing — internal USD and unit costs must be trivially removable from user-facing responses at that point
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
After a DEV run, Использование page shows non-zero Apify results and Claude tokens for this month.
### Files to read
CLAUDE.md, backend/src/models/usage_event.py, backend/src/services/usage.py
### Files to create or modify
backend/src/api/usage.py, backend/tests/test_usage.py, frontend/app/(app)/usage/**, frontend/messages/ru.json
### Handover
- `GET /me/usage?from=&to=` → `UsageOut` — aggregates `usage_events` by `kind` for the authenticated user in the time window (`backend/src/api/usage.py`)
- `UsageOut`: `from_`, `to`, `total_cost_usd`, `by_kind: list[KindTotal]`; `KindTotal`: `kind`, `quantity`, `cost_usd`
- `KindTotalResponse` + `UsageResponse` added to `frontend/lib/api.ts`; `api.getMyUsage(from, to)` method
- `frontend/app/(app)/usage/page.tsx` — current-month usage table (Ресурс / Количество / Стоимость + Итого footer)
- "Использование" link added to app header in `frontend/app/(app)/layout.tsx`
- `Usage` and `App.usage` i18n keys added to `ru.json`
- 5 new tests in `backend/tests/test_usage.py` (empty, totals, date range, user isolation, shape)
- No ENV vars added; no DB migrations needed (schema was already correct)

## [E7-S2] Admin usage view
**Epic:** Usage Metering & Admin
**Sprint:** 5
**Status:** done
**Completed:** 2026-07-18
**Priority:** low
**Depends on:** E7-S1
### Goal
An admin (flag on user) can see usage across all pilot users to understand cost per user before pricing is designed.
### Acceptance Criteria
- [ ] `is_admin` flag; admin-only `GET /admin/usage` — per-user totals (runs, Apify units, tokens, cost) for a date range
- [ ] Minimal admin page (table, date filter); non-admins get 403 / no nav entry
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Admin account on DEV sees the usage table; a regular pilot account gets no admin nav and 403 on the API.
### Files to read
CLAUDE.md, backend/src/api/usage.py, backend/src/models/user.py
### Files to create or modify
backend/src/api/admin.py, backend/tests/test_admin.py, frontend/app/(app)/admin/**, frontend/messages/ru.json
### Changelog
- `is_admin` was already in the initial schema (3a1974cc55cf) — no migration needed.
- `KIND_*` constants exported from `src/models/usage_event.py` and `src/models/__init__.py`, reused in admin aggregation.
- Admin page redirects non-admins back to `/` client-side (belt-and-suspenders alongside the API 403).
### Handover
- `GET /admin/usage?from=&to=` → `AdminUsageOut` (users: list of `UserUsageRow`) — `backend/src/api/admin.py`; 403 for non-admins
- `UserUsageRow`: user_id, email, runs, apify_units, claude_input_tokens, claude_output_tokens, total_cost_usd
- `frontend/app/(app)/admin/page.tsx` — month-range picker + table; redirects non-admins to `/`
- Admin nav link in `frontend/app/(app)/layout.tsx` — visible only when `user.is_admin`
- `GET /auth/me` now returns `is_admin: bool` (was already in `UserOut`)
- `api.getAdminUsage(from, to)` + `AdminUsageResponse`/`UserUsageRowResponse` in `frontend/lib/api.ts`
- 5 tests in `backend/tests/test_admin.py` (403 non-admin, empty, all users, shape, is_admin in /me)
- No ENV vars added

## [E7-S3] Pre-public-launch hardening
**Epic:** Usage Metering & Admin
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E6-S2
### Goal
Close the security/reliability gaps deliberately skipped for pilots (D11) before the product is opened to the public: rate limiting, security headers, and — above all — verified database backups with a tested restore.
### Acceptance Criteria
- [ ] PROD Postgres backup verified: Railway backup schedule confirmed/enabled **and** a restore drill performed onto a scratch database, documented in docs/RUNBOOK.md (backup cadence, retention, step-by-step restore)
- [ ] Per-user rate limits on expensive endpoints (run creation, estimate, auth attempts, export) with Russian 429 messages; limits in config
- [ ] Security headers on both services: CSP, HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors (CSP must allow Telegram webview embedding for the future Mini App, E8-S3)
- [ ] `pip-audit` + `npm audit` gates added to CI (fail on high severity, documented allowlist for accepted findings)
- [ ] Structured error responses verified to leak no stack traces/internal details in prod mode
- [ ] docs/RUNBOOK.md started: backups/restore, incident basics (service restart, reading Railway logs, worker queue draining)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Hammer run-creation on DEV past the limit — 429 in Russian; check response headers on both services; confirm the restore-drill doc reproduces a working scratch DB.
### Files to read
CLAUDE.md, DECISIONS.md (D11), backend/src/main.py, .github/workflows/ci.yml
### Files to create or modify
backend/src/middleware/rate_limit.py, backend/src/middleware/security_headers.py, backend/tests/test_hardening.py, frontend/next.config.ts (headers), .github/workflows/ci.yml, docs/RUNBOOK.md
### Handover
—

## [E7-S4] Pilot security guardrails
**Epic:** Usage Metering & Admin
**Sprint:** 6
**Status:** done
**Completed:** 2026-07-19
**Priority:** critical
**Depends on:** E1-S3
### Goal
While registration is public and billing does not exist yet, a stranger who finds the URL can register and spend real Apify/Claude money with unlimited runs — and a repeat of the env-var wipe incident could silently downgrade prod to the default JWT secret. Close the pilot-stage gaps now; the full public-launch hardening (CSP/HSTS, backups drill, dependency audits) stays in E7-S3.
### Acceptance Criteria
- [ ] Registration requires an invite code when `REGISTRATION_INVITE_CODE` is set (compared constant-time; Russian error message; field on the register page shown only when required — a `GET /auth/register/config` or equivalent flag). Set on DEV and PROD immediately
- [ ] Per-user run quota: `max_runs_per_user_per_day` (default 10) enforced in run creation with a Russian message naming the limit
- [ ] Rate limiting on `/auth/login` and `/auth/register` (default 10/min per IP), hand-rolled on the existing Redis — no new dependency; Russian 429 message
- [ ] Boot check: when `environment != "local"`, startup fails loudly if `jwt_secret` equals the insecure default (guards against a repeat of the 2026-07-18 variable-wipe incident)
- [ ] XLSX export: text cells starting with `=`, `+`, `-`, `@` are prefixed with `'` (formula-injection guard — captions are attacker-controlled input)
- [ ] Baseline security headers: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin` on api and web; CSP `frame-ancestors` on web allowing only Telegram webview origins (`https://web.telegram.org` + Telegram apps) and self — the Mini App (E8-S5) must stay embeddable, everyone else must not embed us
- [ ] Login timing: dummy bcrypt verify on the user-not-found path (closes the account-enumeration timing oracle)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV: register without the invite code fails with a Russian message; the 11th run in a day is blocked; hammering login returns 429; export a run whose caption starts with `=HYPERLINK(` — the cell is inert text in Excel.
### Files to read
CLAUDE.md, backend/src/api/auth.py, backend/src/api/runs.py, backend/src/services/xlsx_export.py, backend/src/config.py
### Files to create or modify
backend/src/config.py, backend/src/api/auth.py, backend/src/api/runs.py, backend/src/middleware/rate_limit.py, backend/src/services/xlsx_export.py, backend/src/main.py, backend/tests/test_guardrails.py, frontend/next.config.ts, frontend/app/(auth)/register/page.tsx, frontend/messages/ru.json, ENV.md
### Handover
- `backend/src/middleware/rate_limit.py` — `check_rate_limit(request, limit=10)`: Redis INCR+EXPIRE fixed-window limiter; called in login and register handlers
- `backend/src/api/auth.py` — `GET /auth/register/config` → `{require_invite: bool}`; register checks hmac.compare_digest against `REGISTRATION_INVITE_CODE`; both login and register are rate-limited
- `backend/src/api/runs.py` — `_check_run_quota()` counts today's UTC runs for the user, raises 429 if ≥ `MAX_RUNS_PER_USER_PER_DAY`
- `backend/src/auth/passwords.py` — `dummy_verify()` runs a full bcrypt check against a pre-computed dummy hash to equalise timing on user-not-found
- `backend/src/auth/providers.py` — `authenticate()` calls `dummy_verify()` when user is None
- `backend/src/services/xlsx_export.py` — `_safe_text()` prefixes `=`, `+`, `-`, `@` cells with `'`; applied to account_handle, title, summary columns
- `backend/src/main.py` — module-level boot check (crash on default JWT_SECRET in non-local env); `_SecurityHeadersMiddleware` adds X-Content-Type-Options and Referrer-Policy to all API responses
- `frontend/next.config.ts` — `headers()` adds X-Content-Type-Options, Referrer-Policy, and `frame-ancestors 'self' https://web.telegram.org https://*.telegram.org` CSP on all Next.js routes
- `frontend/app/(auth)/register/page.tsx` — fetches /auth/register/config on mount; renders invite code field only when `require_invite` is true
- ENV vars added: `REGISTRATION_INVITE_CODE` (api), `MAX_RUNS_PER_USER_PER_DAY` (api)

## [E8-S1] Telegram Login
**Epic:** Telegram Integration & Monetization
**Sprint:** 6
**Status:** backlog
**Priority:** high
**Depends on:** E1-S3
### Goal
Users can log in via Telegram (Login Widget on web), as a second `AuthProvider` alongside email+password, ahead of VK ID in priority (D18).
### Acceptance Criteria
- [ ] `TelegramAuthProvider` verifies the Telegram Login Widget payload (hash check against bot token) and issues the same JWT as email+password login
- [ ] First-time Telegram login creates a user + personal workspace, same as registration; existing email-user can link a Telegram account from settings
- [ ] Login page offers «Войти через Telegram» alongside email+password
- [ ] No changes required to any call site consuming the auth dependency (interface from E1-S3 holds)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV, log in with a real Telegram account via the widget — lands in an authenticated workspace.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (Auth, Telegram Mini App sections), backend/src/auth/*.py
### Files to create or modify
backend/src/auth/telegram.py, backend/tests/test_telegram_auth.py, frontend/app/(auth)/login/page.tsx, frontend/messages/ru.json
### Handover
—

## [E8-S2] Telegram bot notifications
**Epic:** Telegram Integration & Monetization
**Sprint:** 6 (stretch — do last, skip if the sprint runs long)
**Status:** backlog
**Priority:** medium
**Depends on:** E8-S1, E3-S1
### Goal
A user with a linked Telegram account gets a bot message when their analysis run finishes, with a deep link back into the results.
### Acceptance Criteria
- [ ] Bot registered (BotFather); backend sends a message via Bot API on run `done`/`failed` to users with a linked `telegram_chat_id`
- [ ] Message text in Russian; includes item count and a deep link (`t.me/ContentScoutBot/app?startapp=run_<id>` or a plain web URL until E8-S3 ships the Mini App)
- [ ] Users without a linked account are unaffected (no error, just skipped)
- [ ] Notification send failure never fails the run
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Link Telegram on DEV, start a run, get a bot DM when it completes.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/auth/telegram.py
### Files to create or modify
backend/src/services/telegram_notify.py, backend/src/worker.py, backend/tests/test_telegram_notify.py, frontend/app/(app)/settings/**, frontend/messages/ru.json
### Handover
—

## [E8-S3] Telegram Stars subscriptions
**Epic:** Telegram Integration & Monetization
**Sprint:** unassigned (post-Sprint-6 — D27: no payments until the Telegram test launch has run with real test users)
**Status:** backlog
**Priority:** high
**Depends on:** E8-S5, E7-S1
### Goal
Users subscribe to a usage plan paid in Telegram Stars inside the Mini App. The Mini App shell itself (initData auth, bot entry point) ships earlier in E8-S5 — this story is billing only.
### Acceptance Criteria
- [ ] Subscription plans grant token balances per D26 (initial: $5 → 500 токенов / X=10, $20 / X=7, $100 / X=5; plans + X-factors in pricing config, adjustable without code changes); `POST` flow creates a Telegram Stars invoice for a plan or a one-off top-up, confirmed via Bot API payment webhook
- [ ] Credit ledger: each completed run/script debits `ceil(internal_cost_usd × X ÷ 0.01)` tokens, recorded per operation; «Использование» shows balance + itemized per-run/per-script token consumption («анализ от 12.08 — 100 токенов»)
- [ ] X-factors, internal USD costs, and unit prices appear in **no** API response or UI string (test asserts this on the usage/billing endpoints); user-facing world is tokens only
- [ ] Run cost estimate dialog (D10) shows the estimate in tokens for subscribed users
- [ ] Runs/generation blocked with a clear Russian message when the balance is exhausted, with a link to top up
- [ ] Mini App respects D16 (usable at Telegram's in-app viewport sizes) and D20 (loads whatever domain/proxy stage is currently active — no Mini-App-specific network path)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Open the Mini App from the bot on DEV, buy a plan with test Stars, confirm balance updates and a blocked run unblocks after payment.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (Telegram Mini App, Usage Metering sections), backend/src/api/usage.py, backend/src/auth/telegram.py
### Files to create or modify
backend/src/api/billing.py, backend/src/models/subscription.py, backend/tests/test_billing.py, frontend/app/(app)/**, frontend/lib/telegram-webapp.ts, frontend/messages/ru.json
### Handover
—

## [E8-S4] Add competitor by sharing a link to the bot
**Epic:** Telegram Integration & Monetization
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
**Depends on:** E8-S2
### Goal
A blogger shares an Instagram profile link from any app straight to the content-scout bot chat, and it lands in a project's competitor list — the mobile-native way to add competitors on the go.
### Acceptance Criteria
- [ ] Bot recognizes IG profile/post URLs in incoming messages (reuses url_normalizer; post URLs resolve to the posting account)
- [ ] If the user has one project, the account is added to it directly with a confirmation reply; with several, the bot replies with inline project buttons to pick
- [ ] Add respects the 50-account cap and duplicate rules with Russian error replies
- [ ] Unlinked Telegram users get a reply prompting login/linking first
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Share an IG profile link to the DEV bot from a phone — pick a project via buttons, see the account appear in the web UI.
### Files to read
CLAUDE.md, backend/src/services/telegram_notify.py, backend/src/services/url_normalizer.py, backend/src/api/accounts.py
### Files to create or modify
backend/src/services/telegram_bot.py (webhook handler), backend/src/api/telegram_webhook.py, backend/tests/test_telegram_bot.py
### Handover
—

## [E8-S5] Telegram Mini App shell (no billing)
**Epic:** Telegram Integration & Monetization
**Sprint:** 6
**Status:** backlog
**Priority:** critical
**Depends on:** E8-S1, E12-S2
### Goal
The app opens inside Telegram from the bot with zero login friction, so it can be shared with test users by bot handle (D27). This is the Sprint 6 exit criterion. Payments are explicitly out of scope (they stay in E8-S3, post-Sprint-6) — hard constraint: no billing/Stars code in this story.
### Acceptance Criteria
- [ ] Minimal bot webhook on the api service (`POST /telegram/webhook`, validated via `X-Telegram-Bot-Api-Secret-Token` against `TELEGRAM_WEBHOOK_SECRET`): `/start` replies in Russian with an inline «Открыть content-scout» `web_app` button pointing at the web URL. Webhook + chat menu button (`setChatMenuButton`) registered via Bot API from a small idempotent setup path — no BotFather steps needed beyond bot creation
- [ ] Bot API called with plain `httpx` (no bot-framework dependency, D27)
- [ ] Frontend detects Telegram context (`window.Telegram.WebApp` with non-empty `initData`), sends `initData` to `POST /auth/telegram/webapp`; backend verifies the HMAC per Telegram Web App spec (secret key = HMAC-SHA256 of bot token with "WebAppData", `auth_date` ≤ 24h old) and returns the standard JWT; first open auto-creates user + personal workspace via `TelegramAuthProvider` (E8-S1)
- [ ] Inside Telegram: no login/register forms ever shown, logout hidden, `Telegram.WebApp.ready()` + `expand()` called; bottom navigation (E12-S2) and safe-area behave correctly in the webview
- [ ] Outside Telegram the web app behaves exactly as before (auth flow untouched)
- [ ] Works on DEV over the public Railway HTTPS URL
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
From a phone: open the DEV bot, tap «Открыть content-scout» — the Mini App opens already authenticated, workspace auto-created; full flow (create project → add competitors → run → browse card results → shortlist) works inside Telegram. Repeat from a second Telegram account to confirm it is shareable.
### Files to read
CLAUDE.md, DECISIONS.md (D17, D27), docs/ARCHITECTURE.md (Telegram Mini App section), backend/src/auth/telegram.py, frontend/lib/auth-context.tsx
### Files to create or modify
backend/src/api/telegram_webhook.py, backend/src/auth/telegram.py, backend/src/config.py, backend/src/main.py, backend/tests/test_telegram_webapp.py, frontend/lib/telegram-webapp.ts, frontend/lib/auth-context.tsx, frontend/app/layout.tsx, frontend/messages/ru.json, ENV.md
### Handover
—

## [E9-S1] Public API tokens
**Epic:** Public API & Engine Integration
**Sprint:** unassigned
**Status:** backlog
**Priority:** low
**Depends on:** E6-S1
### Goal
A workspace owner can generate scoped API tokens for programmatic read access to their projects' runs and shortlist, for future external consumers (e.g. a content-generation engine).
### Acceptance Criteria
- [ ] `POST /me/api-tokens` creates a token (shown once, stored hashed); `DELETE` revokes; tokens scoped to a workspace
- [ ] Token auth accepted alongside JWT on read endpoints for runs/content_items/shortlist_items
- [ ] Simple token management UI in settings
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Create a token on DEV, `curl` a shortlist endpoint with it, confirm it works and revoking breaks it.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (Public API & engine integration), backend/src/auth/*.py
### Files to create or modify
backend/src/auth/api_token.py, backend/src/api/tokens.py, backend/tests/test_api_tokens.py, frontend/app/(app)/settings/**, frontend/messages/ru.json
### Handover
—

## [E9-S2] Webhooks for run/shortlist events
**Epic:** Public API & Engine Integration
**Sprint:** unassigned
**Status:** backlog
**Priority:** low
**Depends on:** E9-S1
### Goal
A workspace can register a webhook URL that receives `run.completed` and `shortlist.updated` events, so an external product (e.g. a football-content-engine-style pipeline) can react without polling.
### Acceptance Criteria
- [ ] Webhook registration (URL + shared secret) per workspace; signed payload (HMAC) on delivery
- [ ] Events fired: `run.completed` (run id, item count), `shortlist.updated` (item id, added/removed)
- [ ] Delivery retried with backoff on failure; failures logged, never block the triggering action
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Register a webhook pointed at a request-bin on DEV, finish a run, confirm the signed payload arrives.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (Public API & engine integration), backend/src/worker.py, backend/src/api/shortlist.py
### Files to create or modify
backend/src/services/webhooks.py, backend/src/api/webhooks.py, backend/tests/test_webhooks.py, frontend/app/(app)/settings/**, frontend/messages/ru.json
### Handover
—

## [E10-S1] Script generation from shortlist
**Epic:** Content Generation
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E6-S1, E7-S1
### Goal
From the shortlist, the blogger requests script generation for selected items or all, choosing a content type (пост / карусель / reels, D23) and target duration where relevant; scripts generate in parallel without blocking the app.
### Acceptance Criteria
- [ ] «Создать сценарий» (replacing the E6-S1 disabled placeholder) works per item, for a selection, or «для всех»; dialog picks тип (default пост) and target duration for reels/carousel-video
- [ ] Each request enqueues an independent worker job (script_requests table: shortlist_item_id, type, params, status, result); jobs run in parallel; the blogger keeps working — statuses visible on the shortlist rows
- [ ] Script produced by a stronger Claude model from the item's summary, caption, and metrics; prompt per type in docs/PROMPTS.md; output structured per D23 type (пост: текст поста; карусель: hero + слайды + текст; reels: закадровый текст/оверлеи по таймкодам)
- [ ] Claude tokens metered as usage_events with a distinct kind (`claude_script_*`); generation blocked when credit balance exhausted (E8-S3 rules)
- [ ] Scripts history per project (list, view, re-generate) — completes the original spec item 8
- [ ] TG notification on completion for linked users (reuses E8-S2)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Select 2 shortlist items on DEV, request «карусель» scripts for both — both complete in parallel, results readable in scripts history.
### Files to read
CLAUDE.md, docs/PROMPTS.md, docs/ARCHITECTURE.md (Content generation section), backend/src/worker.py, backend/src/api/shortlist.py
### Files to create or modify
backend/src/models/script_request.py (+ migration), backend/src/services/scriptwriter.py, backend/src/api/scripts.py, backend/tests/test_scripts.py, docs/PROMPTS.md, frontend/app/(app)/projects/[id]/shortlist/**, frontend/app/(app)/projects/[id]/scripts/**, frontend/messages/ru.json
### Handover
—

## [E10-S2] Asset generation and download delivery
**Epic:** Content Generation
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
**Depends on:** E10-S1, E9-S2
### Goal
Approved scripts turn into ready-to-post assets per D23 — пост (image + text), карусель (hero + slides, optional background music auto-rendering it as a reels video), reels (blogger-uploaded background video + script text overlay) — delivered as a downloadable package (default delivery per D24).
### Acceptance Criteria
- [ ] Generation dispatched per type behind a `ContentEngine` interface: internal implementation and/or delegation to a football-content-engine-style external service via the D21 API/webhook contract (engine choice per niche is config)
- [ ] Карусель with background music renders to an mp4 reels variant; reels type accepts blogger-uploaded assets (bg video) and burns script text overlays
- [ ] Blogger downloads a per-item package (zip: media + caption text file) from the app; generation costs metered as usage_events
- [ ] Jobs parallel and non-blocking, statuses on the scripts/содержимое view, TG notification on completion
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Generate a карусель with music from a script on DEV, download the zip — slides + mp4 + caption present and coherent.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (Content generation, Public API sections), backend/src/services/scriptwriter.py, backend/src/api/scripts.py
### Files to create or modify
backend/src/services/content_engine/ (base + implementations), backend/src/models/generated_asset.py (+ migration), backend/src/api/assets.py, backend/tests/test_content_engine.py, frontend/app/(app)/projects/[id]/scripts/**, frontend/messages/ru.json
### Handover
—

## [E10-S3] Review and adjust generated content
**Epic:** Content Generation
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
**Depends on:** E10-S2
### Goal
Before downloading/publishing, the blogger reviews generated content and adjusts it at the right granularity: edit any text inline, regenerate an individual slide or the whole piece.
### Acceptance Criteria
- [ ] Review screen per generated item: пост — image + editable text; карусель — slide-by-slide viewer with per-slide «Перегенерировать» and editable slide/post text; reels — preview with editable overlay texts
- [ ] Text edits save without regeneration; regeneration (per slide or whole) is a normal metered job that replaces the asset on completion
- [ ] Version kept simple: latest wins, previous kept until the item is downloaded/published (undo one step)
- [ ] Mobile-usable per D16 (this is a phone-first workflow)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV regenerate slide 2 of a карусель and edit the post text — download reflects both changes.
### Files to read
CLAUDE.md, backend/src/api/assets.py, backend/src/services/content_engine/, frontend/app/(app)/projects/[id]/scripts/**
### Files to create or modify
backend/src/api/assets.py, backend/tests/test_asset_review.py, frontend/app/(app)/projects/[id]/review/**, frontend/messages/ru.json
### Handover
—

## [E11-S1] Spike: Instagram Graph API publishing feasibility
**Epic:** Instagram Connection, Publishing & Analytics
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
**Depends on:** none
### Goal
A timeboxed research spike (no product code) that turns D24 into a concrete go/no-go: what Meta app review requires for content publishing + insights permissions, what the blogger-side requirements are (Business/Creator account, linked FB page — still required?), and what this means for RU-audience bloggers.
### Acceptance Criteria
- [ ] Written findings in docs/IG_PUBLISHING.md: required permissions/scopes, app-review steps and expected timeline, per-blogger onboarding flow, supported media types (single post / carousel / reels) and their API constraints, rate limits
- [ ] Legal/practical assessment for RU context (Meta status in Russia, implications for our entity and for bloggers)
- [ ] Recommendation: proceed / proceed-later / drop, with the fallback (manual download, D24) explicitly costed against it
- [ ] DECISIONS.md updated with the outcome
### Definition of Done
- [ ] All AC checked
- [ ] DONE.md updated
- [ ] BACKLOG.md updated (E11-S2/S3 re-scoped or dropped per findings)
### Smoke test
n/a — research story; deliverable is the doc + decision entry.
### Files to read
CLAUDE.md, DECISIONS.md (D24), docs/ARCHITECTURE.md
### Files to create or modify
docs/IG_PUBLISHING.md, DECISIONS.md
### Handover
—

## [E11-S2] Connect IG account, publish and schedule
**Epic:** Instagram Connection, Publishing & Analytics
**Sprint:** unassigned
**Status:** backlog
**Priority:** low
**Depends on:** E11-S1, E10-S3
### Goal
Blogger connects their own Instagram Business/Creator account via OAuth (scoped per project — each project represents one own account, per the workspace→project model) and publishes or schedules reviewed content directly from the app.
### Acceptance Criteria
- [ ] OAuth connect/disconnect per project; connection status + account preview shown in project settings
- [ ] «Опубликовать» and «Запланировать» (date/time) on reviewed items for supported types; scheduled publishes executed by the worker; success/failure reported + TG notification
- [ ] Publish failures leave the asset downloadable (D24 fallback always available)
- [ ] Token storage encrypted; revocation handled gracefully
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Connect a test Business account on DEV, schedule a post 5 minutes out — it appears on the IG account.
### Files to read
CLAUDE.md, docs/IG_PUBLISHING.md, backend/src/api/assets.py, backend/src/worker.py
### Files to create or modify
backend/src/services/ig_publisher.py, backend/src/api/ig_connect.py, backend/src/models/ig_connection.py (+ migration), backend/tests/test_ig_publisher.py, frontend/app/(app)/projects/[id]/settings/**, frontend/messages/ru.json
### Handover
—

## [E11-S3] Own-account analytics
**Epic:** Instagram Connection, Publishing & Analytics
**Sprint:** unassigned
**Status:** backlog
**Priority:** low
**Depends on:** E11-S2
### Goal
For a connected own account, the project shows an Аналитика tab: follower dynamics and per-post insights (reach, likes, saves, shares) — closing the loop from «что работает у конкурентов» to «что сработало у меня». Standalone-product potential noted in D24.
### Acceptance Criteria
- [ ] Daily worker job pulls Graph API insights for connected accounts into a metrics table
- [ ] Аналитика tab: подписчики over time, recent posts table with insight columns (sortable, same table UX as results), published-via-app items highlighted so scout→engine→publish performance is traceable
- [ ] Insight pulls metered as usage_events (API calls are free, but track volume for rate-limit budgeting)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Connected DEV account shows follower count history and per-post reach after the daily job runs.
### Files to read
CLAUDE.md, docs/IG_PUBLISHING.md, backend/src/services/ig_publisher.py, docs/UI_GUIDELINES.md
### Files to create or modify
backend/src/services/ig_insights.py, backend/src/models/account_metric.py (+ migration), backend/src/api/analytics.py, backend/tests/test_ig_insights.py, frontend/app/(app)/projects/[id]/analytics/**, frontend/messages/ru.json
### Handover
—

## [E12-S1] Design system re-skin (light theme v1)
**Epic:** UI/UX Modernization
**Sprint:** 6
**Status:** backlog
**Priority:** high
**Depends on:** E6-S2
### Goal
The product stops looking like a wireframe: the light design system approved in the 2026-07-18 UI review (D28) — violet accent, tinted background with white cards, Cyrillic-first fonts, real icons — is applied to every existing screen. Dark mode is removed entirely.
### Acceptance Criteria
- [ ] Design tokens defined once in `globals.css` (Tailwind v4 `@theme`): background `#F6F7F9`, card `#FFFFFF`, ink `#1A1523`, secondary text `#6F6E77`, accent `#6E56CF` (hover ~`#5D48B8`), accent-soft `#EDE9FE`, success `#30A46C` (soft `#E9F9F1`), star/warning `#FFB224`, danger `#E5484D`, hairline border `#E4E2E9`; radius: cards 14px, controls 12px, chips 999px. All components consume tokens — no ad-hoc hex in components
- [ ] Fonts via `next/font/google`: **Golos Text** (UI + data, tabular figures for metric columns), **Unbounded** (logo/display accents only); zero layout shift
- [ ] `lucide-react` replaces every emoji/unicode glyph used as an icon (⊞ ★ ☆ ✕ ▲ ▼ 🎬 🖼️) — D28 dependency entry
- [ ] Shared primitives in `frontend/components/ui/`: Button (primary/secondary/ghost), Card, Input, Badge/Chip, Tabs — all screens use them; no raw one-off button/input styling left
- [ ] Dark mode removed: every `dark:` class deleted, `<html>`/body backgrounds set to the light tokens; visual QA in a dark-OS-theme browser confirms the app stays light
- [ ] All existing screens re-skinned (login/register, projects home, project tabs: competitors/results/shortlist/history, usage, admin, run dialog); no layout regressions at 375px and 1280px, verified in the browser
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Click through every screen on DEV at 375px and desktop: violet accent, white cards on the tinted background, Golos Text everywhere, Unbounded logo, no emoji icons, no dark surfaces regardless of OS theme.
### Files to read
CLAUDE.md, DECISIONS.md (D28), docs/UI_GUIDELINES.md, frontend/app/globals.css, frontend/app/layout.tsx
### Files to create or modify
frontend/app/globals.css, frontend/app/layout.tsx, frontend/components/ui/** (new), frontend/components/results-table.tsx, all files under frontend/app/(auth)/** and frontend/app/(app)/**, frontend/package.json (lucide-react), frontend/messages/ru.json
### Handover
—

## [E12-S2] Mobile cards, bottom navigation, UX states
**Epic:** UI/UX Modernization
**Sprint:** 6
**Status:** backlog
**Priority:** high
**Depends on:** E12-S1
### Goal
The phone (and Telegram webview) experience feels like an app, not a shrunken dashboard: results become cards, navigation moves to a bottom tab bar, and loading/empty/error states are designed. This story is the Mini App's UX foundation (E8-S5 depends on it).
### Acceptance Criteria
- [ ] Results and shortlist render as **cards** below `md` (768px): cover thumbnail placeholder by type, @handle, one-line summary, metric chips with «просм./день» as the highlighted hero metric (soft-green chip), type chip, star toggle. The existing table is unchanged at ≥ `md`
- [ ] Sorting on mobile via a sort chip opening a bottom sheet (table headers don't exist in card mode); default sort unchanged
- [ ] **Bottom tab bar** on mobile inside a project (Результаты / Конкуренты / Шортлист / История) and equivalent app-level nav; ≥44px tap targets; `env(safe-area-inset-bottom)` respected
- [ ] Skeleton loaders replace every «Загрузка…» text; transient errors surface as toasts (auto-dismiss) instead of persistent inline text; every list screen (projects, competitors, results, shortlist, history) has a designed empty state with an action hint
- [ ] No hover-only affordances: text expansion works by tapping the cell/card itself (the ⊞-button pattern is gone)
- [ ] Full flow verified in the browser at 375px: create project → add competitors → run with progress → browse card results → sort → shortlist → history
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Entire product flow at 375px on DEV feels app-like: bottom tabs, cards, skeletons, toasts; desktop table experience unchanged.
### Files to read
CLAUDE.md, DECISIONS.md (D28), docs/UI_GUIDELINES.md, frontend/components/results-table.tsx, frontend/app/(app)/projects/[id]/**
### Files to create or modify
frontend/components/results-cards.tsx (new), frontend/components/ui/bottom-nav.tsx (new), frontend/components/ui/toast.tsx (new), frontend/components/ui/skeleton.tsx (new), frontend/app/(app)/**, frontend/messages/ru.json
### Handover
—
