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
- **E13 Navigation & Details Restructure** — bottom nav collapses to Детали/Результаты/Анализ; new Details dashboard (KPI card, links to Competitors/Scheduled Runs, run-history cards, create-run entry point); Competitors page trimmed of selection UI
- **E14 Scheduled Runs** — recurring analysis on a day-of-week + time schedule, new arq cron infra, Telegram summary notification on completion
- **E15 Run Detail View** — opening a run from Details shows Summary (AI overview of what competitors post about, top viral topics, top 5 posts) and Publications tabs
- **E16 Analysis Teaser** — placeholder page for future paid deep-analysis products (competitor/run/publication deep-dive, script rewrite)
- **E17 Run Deep Analysis** — paid add-on fulfilling E16-S1's "Разбор запуска" teaser card: on-demand deep analysis of one completed run's publications + comments (topic/format/hook frequency vs. virality, comment sentiment/complaints/praises/unanswered-questions), producing a two-tab Статистика/Рекомендации report; metered in tokens at a markup over internal cost (D26, D35)

Post-MVP (not scheduled, first stories drafted below for E8–E11): VK ID + SMS auth (behind Telegram Login in priority per D18), YouTube/TikTok/Threads platforms, native mobile app (not planned — see D17), team workspaces, RU infra migration stages 2–3 (D20, infra-only, tracked outside BACKLOG.md until scheduled). Mobile card layout for tables is now scheduled (E12-S2, Sprint 6 — supersedes the horizontal-scroll-only clause of D16 per D28).

**2026-07-21 reprioritization — tuning toward a single-blogger MVP:** E2-S3, E5-S3, E5-S4 (competitor follower count + comments column), E5-S5 (virality score, new) are next up; E8-S6 (Telegram Mini App bootstrap fix, new) is critical and blocking the pilot. Everything else currently `backlog` (E3-S3, E3-S4, E3-S5, E7-S3, E8-S4, E9-S1, E9-S2, E10-S1, E10-S2, E10-S3, E11-S1, E11-S2, E11-S3) is explicitly deferred post-MVP — see each story's `Sprint:` line for why.

**2026-07-22 execution plan — locked, extends the MVP:** Sprint 7 shipped (see DONE.md) plus two untracked-but-real feature batches now backfilled as stories: E12-S3 (mobile results controls consolidation + polish) and E3-S7 (run scope: last-N-publications mode). New epics E13–E16 (Details/nav restructure, scheduled runs, run-detail Summary+Publications tabs, Analysis teaser) are locked for **Sprint 8** (E13, E16, E15 — reshape the IA) and **Sprint 9** (E14 — needs new arq cron infra). E8-S3 (Telegram Stars subscription) is re-scoped per D30 (single 1990₽/2000-token tier) and slotted for **Sprint 10**, after the new IA lands so its entry point has a home.

**2026-07-25 brainstorm session — new epic drafted, not yet scheduled:** E17 (Run Deep Analysis) fleshes out E16-S1's "Разбор запуска" teaser card into a real paid product — nine stories, E17-S1..S9, drafted below. `Sprint: unassigned`, proposed for **Sprint 11** (after Sprint 10's E8-S3, so it has a working token-purchase flow behind it — though note the token *deduction* mechanism this epic reuses is already live, per `worker.py`/`api/runs.py`, independent of E8-S3 shipping). Comment scraping is dual-vendor (Bright Data primary, Apify fallback — D32); the token pricing multiplier is deliberately left unset pending a real pilot run's `usage_events` (D35) rather than assumed from the base run's flat per-item rate. See D32–D35.

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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** 7
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E2-S2, E5-S4 (reuse `Platform.fetch_profile()` built there rather than re-implementing the details fetch)
### Goal
The Конкуренты list shows basic live details per account — display name/title, follower count, avatar — fetched when an account is added and refreshed on each analysis run.
### Acceptance Criteria
- [x] `Platform` interface gains `fetch_profile(account) -> ProfileInfo` (display_name, followers, avatar_url); Apify IG profile fetch implements it — E5-S4 already added `fetch_profile`/`followers_count`; this story extends `ProfileInfo` with `display_name`/`avatar_url` and wires `InstagramPlatform` to Apify's `fullName`/`profilePicUrl` detail fields
- [x] Profile fetched async on account add (list shows the row immediately, details fill in); refreshed as part of every run's scraping phase
- [x] Конкуренты list displays: аватар, название, @handle, подписчики (formatted ru-RU), последнее обновление
- [x] Profile fetches write `apify_result` usage_events like any other scrape
- [x] Fetch failure leaves the row usable (handle + «нет данных»), never blocks add/run
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (3 new `test_profile_enrichment.py` tests, `InstagramPlatform.fetch_profile` normalization extended, `test_accounts.py` updated to mock the new enqueue call; mypy + ruff clean; DB-backed tests are CI-only, no local Postgres in this sandbox)
- [ ] CI green, deployed to DEV — pending this push
- [ ] Smoke test — DEFERRED (requires a real DEV account add against a public IG profile; same deferral pattern as every Apify-touching story)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Add a real public IG account on DEV — name, followers, and avatar appear within a minute.
### Files to read
CLAUDE.md, backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/api/accounts.py
### Files to create or modify
backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/models/account.py (+ migration), backend/tests/test_profile_enrichment.py, frontend/app/(app)/projects/[id]/competitors/**, frontend/messages/ru.json
### Changelog
- Added a dedicated `fetch_account_profile(ctx, account_id, user_id)` arq job (registered in `WorkerSettings.functions` alongside `run_analysis`) rather than calling Apify from the accounts router — CONVENTIONS.md forbids external calls from routers, so "profile fetched async on account add" needed its own background job, separate from the analysis-run lifecycle. `POST /projects/{id}/accounts` enqueues one job per newly added account (via `services/queue.py:enqueue_profile_fetch`, mirroring the existing `enqueue_run` pattern) right after commit.
- `user_id` travels with the enqueue call rather than being re-derived in the worker via an Account→AccountList→Project→Workspace→WorkspaceMember join — the router already has `CurrentUser` in scope, so passing it through is simpler than adding a new reverse-lookup service function for a single call site.
- Reused E5-S4's `Account.followers_updated_at` as the shared "last profile fetch" timestamp for `display_name`/`avatar_url`/`followers_count` too, instead of adding a second timestamp column — all three fields come from the same `fetch_profile()` call, so one column covers "last updated" for the whole profile.
- Renamed the Конкуренты page's pre-existing (backend-unpopulated) `AccountResponse.follower_count` stub to `followers_count` to match this story's and E5-S4's model/API naming, and replaced its "K"/"M" abbreviation style with the same ru-RU "тыс."/"млн" formatter used in the Результаты table, for consistency across the app.
- «нет данных» renders only when *both* `display_name` and `followers_count` are null (i.e., the profile fetch never succeeded even once) — a partially-filled profile (e.g. followers but no avatar) still renders what it has rather than falling back to the generic message.
- **Post-merge CI fix (2026-07-22):** the first version of `fetch_account_profile` did all its work inline in the arq wrapper (opened its own session via `get_sessionmaker()`), which passed locally (no DB available to catch it) but failed in CI — the test called the wrapper directly, and the test fixture's session lives inside an outer transaction that's never really committed to Postgres, so a second, independently-opened connection from `get_sessionmaker()` couldn't see the test's own uncommitted data. Fixed by splitting it into `apply_profile_update(session, account, user_id)` (core logic, takes an already-open session) + `fetch_account_profile(ctx, account_id, user_id)` (thin arq wrapper that opens the session and delegates) — the exact same split `process_run`/`run_analysis` already uses, and for the same reason. Tests now call `apply_profile_update` directly with the test's injected session.
### Handover
- `src/platforms/base.py:ProfileInfo` now carries `display_name`/`avatar_url` alongside E5-S4's `followers_count`; `InstagramPlatform._fetch_profile_once` maps Apify's `fullName`→`display_name`, `profilePicUrl` (falling back to `profilePicUrlHD`)→`avatar_url`. `MockPlatform.fetch_profile` returns fixed test values for all three.
- `Account.display_name` / `Account.avatar_url` — migration `e4f5a6b7c8d9` (now head, was `d3e4f5a6b7c8`).
- `src/worker.py:apply_profile_update(session, account, user_id)` is the testable core (mirrors `process_run`); `fetch_account_profile(ctx, account_id, user_id)` is the thin arq wrapper. On any fetch exception, `apply_profile_update` returns silently (row keeps whatever it had, `handle` always usable) and writes no usage event. `process_run`'s existing per-run profile fetch (E5-S4) now also updates `display_name`/`avatar_url`, not just `followers_count`.
- **Any future worker job that touches the DB should follow this same split from the start** — a thin `async def foo(ctx, ...)` wrapper that only opens a session and delegates, plus a `foo_core(session, ...)` (or similarly named) function that takes an already-open session and is what tests actually call. Calling the raw arq-registered function directly from a test only works by accident when it happens to not need to see anything the test committed.
- `src/services/queue.py:enqueue_profile_fetch(account_id, user_id)` — call after adding accounts; `src/api/accounts.py:add_accounts` calls it once per newly added account post-commit.
- `AccountOut` (`src/api/accounts.py`) gained `display_name`, `followers_count`, `avatar_url`, `profile_updated_at` (API-facing alias for the `followers_updated_at` column — chosen so the response contract doesn't imply the timestamp is followers-specific).
- Frontend: `frontend/app/(app)/projects/[id]/competitors/page.tsx` — row now shows an avatar circle (Users icon fallback), display_name as primary text with `@handle` + followers + "обновлено DD.MM" as secondary text, or «нет данных» when nothing has been fetched yet. New `Competitors.noData`/`Competitors.updatedLabel` i18n keys.
- Next story in this sprint (E5-S3, comments column) touches `api/items.py`/`results-table.tsx`/`xlsx_export.py` only — no overlap with this story's files.

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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — user reconfirmed post-MVP after reviewing: E7-S4's daily run quota + E4-S3's ~4× Claude cost cut already cover most of the risk this story guards against)
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

## [E5-S3] Comments count column
**Epic:** Results Table & Export
**Sprint:** 7
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E5-S1
### Goal
The results table and XLSX export show each publication's comments count — the data is already scraped into `content_items.comments` (E3-S2) but never surfaced past the DB.
### Acceptance Criteria
- [x] `ContentItemOut` (`GET /runs/{id}/items`) includes `comments`
- [x] Результаты table gains a sortable "Комментарии" column, positioned near лайки/просмотры
- [x] XLSX export includes a matching "Комментарии" column/header
- [x] Existing sort/pagination/NULL-handling for other columns unaffected
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (new sort-by-comments test in `test_items_api.py`, shape assertion updated, `test_export.py` header/value assertions updated; mypy + ruff + `tsc --noEmit` + `next lint` clean; DB-backed tests are CI-only, no local Postgres in this sandbox)
- [ ] CI green, deployed to DEV — pending this push
- [ ] Smoke test — DEFERRED (requires a real finished DEV run; same deferral pattern as every Apify-touching story)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Open a finished run on DEV — «Комментарии» column shows plausible counts, sorts correctly; export to Excel and confirm the column is present with matching values.
### Files to read
CLAUDE.md, backend/src/api/items.py, backend/src/models/content_item.py, frontend/components/results-table.tsx, backend/src/services/xlsx_export.py
### Files to create or modify
backend/src/api/items.py, backend/tests/test_items_api.py, frontend/components/results-table.tsx, frontend/messages/ru.json, backend/src/services/xlsx_export.py, backend/tests/test_export.py
### Changelog
- No migration needed — `content_items.comments` has existed since E3-S2, this story only surfaces it through the API/UI/export.
- `ContentItem` was already selected in full in both `items.py`'s and `export.py`'s queries, so `item.comments` needed no new `select()` column — same pattern as the pre-existing `likes`/`views` fields.
- The desktop Результаты table has no `views` column today (removed in an earlier UI pass — IG doesn't expose view counts for most post types, judged "misleading" at the time), so "positioned near лайки/просмотры" became "positioned right after Лайки", the closest equivalent still on screen.
- Scoped to the desktop table + XLSX export only, matching the story's file list — didn't add comments to the mobile card view (`results-cards.tsx`) or the shortlist table/export, since neither was in AC and comments is a secondary metric compared to the primary card chips already shown.
### Handover
- `ContentItemOut.comments` (`api/items.py`, `api/export.py`) — passthrough from `ContentItem.comments`; `"comments"` added to the `SortField` literal and both routers' `sort_columns` maps.
- `results-table.tsx` — new sortable "comments" column between "likes" and "days_since_published"; `frontend/lib/api.ts` `ContentItemResponse`/`ItemSortField` updated to match.
- `xlsx_export.py` — "Комментарии" header inserted after "Просмотры" (position 10 of 13); no column-index shift for the earlier "Ссылка" hyperlink cell since it sits before likes/views/comments.
- Next story in this sprint (E5-S5, virality score) reads `metrics.py`/`items.py`/`results-table.tsx`/`xlsx_export.py` — no direct file conflicts with this story, but it will be inserting yet another column into the same three places; worth checking column order holistically rather than always appending at the end.

## [E5-S4] Subscriber count next to account name
**Epic:** Results Table & Export
**Sprint:** 7
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E3-S2
### Goal
The Результаты table shows each account's current follower count next to its name, fetched once per account per run. Instagram doesn't return follower count alongside post data — confirmed against Apify's `instagram-scraper` docs, `resultsType: "details"` is a separate call from `resultsType: "posts"` — so this adds one extra Apify call per **account** per run (not per publication). This story introduces `Platform.fetch_profile()`; the still-backlogged E2-S3 (Competitor profile enrichment, Конкуренты list) can build on the same method rather than re-implementing the details fetch.
### Acceptance Criteria
- [x] `Platform` interface gains `fetch_profile(account) -> ProfileInfo` (at minimum `followers_count`); `InstagramPlatform` implements it via Apify `resultsType: "details"`
- [x] Worker fetches profile info once per account per run during the scraping phase (not per item); `Account` gains `followers_count` + `followers_updated_at` columns (+ migration) so the latest known count persists between runs
- [x] Profile fetch writes an `apify_result` usage_events row like any other scrape; failure never fails the account's content scrape (falls back to the last known value, or blank if none yet)
- [x] Результаты table shows follower count next to the account name (ru-RU formatted, e.g. "12,4 тыс."); XLSX export includes it
- [x] Unit tests: `fetch_profile` normalization, worker writes/updates `followers_count`, usage_events row written, profile-fetch failure doesn't fail the run
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (3 new InstagramPlatform tests, 2 new worker tests, existing items/export/worker tests updated for the new field — mypy + ruff clean; DB-backed tests are CI-only, no local Postgres in this sandbox, consistent with every prior story)
- [ ] CI green, deployed to DEV — pending this push
- [ ] Smoke test — DEFERRED (requires a real DEV run against public IG accounts; same deferral pattern as every other Apify-touching story in this project)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Run analysis on DEV against 2 real public IG accounts — each row's account name shows a plausible, ru-RU-formatted follower count; usage_events has one extra `apify_result` row per account for the profile fetch.
### Files to read
CLAUDE.md, backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/worker.py, backend/src/models/account.py, backend/src/api/items.py, frontend/components/results-table.tsx
### Files to create or modify
backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/models/account.py (+ migration), backend/src/worker.py, backend/src/api/items.py, backend/tests/test_instagram_platform.py, backend/tests/test_worker.py, frontend/components/results-table.tsx, frontend/messages/ru.json
### Changelog
- Extended the retry loop already in `InstagramPlatform.fetch_content` into a shared generic `_with_retries()` helper (PEP 695 syntax) rather than duplicating the 3-attempt exponential-backoff loop for `fetch_profile` — same behavior, one place to change it.
- Followers usage event is written with `quantity=1` (one profile lookup), kept as its own `apify_result` row rather than folded into the content-fetch row, so the two Apify calls stay independently auditable in `usage_events` — matches "writes an apify_result usage_events row like any other scrape" literally.
- Also updated `frontend/components/results-cards.tsx` (mobile card view, not in the story's file list) to show the same follower count under the account handle — the Mini App's primary UI is the mobile card list (D28/E12-S2), so leaving it out there would make this story invisible to the actual pilot user on their phone.
- XLSX "Подписчики" column inserted right after "Аккаунт" (position 2) — shifted every later column index by one; updated `test_export.py`'s header/hyperlink-column assertions to match.
### Handover
- `src/platforms/base.py:ProfileInfo` (`followers_count: int | None`) — new dataclass; `Platform` Protocol now requires `fetch_profile(account) -> ProfileInfo` on every implementation (`MockPlatform` returns a fixed `12_400`; `InstagramPlatform` calls Apify with `resultsType: "details"`).
- `Account.followers_count` / `Account.followers_updated_at` (migration `d3e4f5a6b7c8`, down_revision `c2275f27bb18` — now head) — updated by the worker once per account per run; untouched (falls back to last known value) when the profile fetch fails.
- `src/worker.py:process_run` — `_fetch_one` now fetches profile and content per account under the same semaphore slot; profile fetch failure is swallowed locally and never surfaces as an account failure or run failure.
- `ContentItemOut.followers_count` (both `api/items.py` and `api/export.py`) — joined from `Account.followers_count` in the same query, no extra round trip.
- Frontend: `formatFollowers()` (in both `results-table.tsx` and `results-cards.tsx` — small enough duplication that a shared util felt like premature abstraction for one 4-line function) renders "12,4 тыс." / "3,1 млн" style; `ResultsTable`/`ResultsCards` `followersShort` i18n key ("подп.") added to their own namespaces.
- E2-S3 (Competitor profile enrichment, next story in this sprint) should reuse `Platform.fetch_profile()` directly rather than re-implementing the details fetch — that was the explicit reason this story introduced the method as a standalone interface member. Note also: the Конкуренты page (`frontend/app/(app)/projects/[id]/competitors/page.tsx`) already has speculative frontend scaffolding for a follower count (`AccountResponse.follower_count`, `formatFollowerCount()`, `followersShort`) from an earlier UI pass, but the backend never populated it — E2-S3 should rename that field to `followers_count` for consistency with this story's model/API naming rather than introduce a second name for the same concept.

## [E5-S5] Virality score (High/Medium/Low) per publication
**Epic:** Results Table & Export
**Sprint:** 7
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E5-S1, E5-S4
### Goal
Each publication in the Результаты table gets a Высокая/Средняя/Низкая virality badge, so a blogger scanning a competitor list can spot standout content at a glance instead of reading raw numbers. Scored **self-relative** — did this post massively outperform *that account's own* recent baseline — rather than against a hardcoded global threshold, since a meme account and a niche B2B account have wildly different normal engagement and an absolute cutoff would be meaningless across a competitor list. A separate `engagement_rate` column (needs E5-S4's follower data) covers the different question of comparing raw performance *across* accounts.
### Acceptance Criteria
- [x] Per-account baseline computed at read time within a run (SQL, alongside the existing `days_since_published`/`views_per_day`/`likes_per_day` builders in `metrics.py` — no new persisted columns): `median(likes + comments)` across that account's items in the run; reels additionally get `median(views)` when the account has recorded view data
- [x] Per item: `performance_ratio = (likes + comments) / account_median`; for reels, combine with `views / account_median_views` (e.g. `max` of the two) so a reel can register as viral via reach (algorithmic push beyond followers) or via raw engagement
- [x] Bucket thresholds are config-driven (`virality_high_ratio` / `virality_low_ratio` in `Settings`, defaults `2.0` / `0.7`), matching the existing tunable-constant pattern from `estimator.py` — not hardcoded
- [x] Accounts with fewer than `virality_min_items` (default `3`) items in the run get no badge ("недостаточно данных") rather than a misleading score off a tiny sample
- [x] Результаты table shows the badge per row (D28 token colors: success for high, neutral bordered chip for medium, muted text for low); XLSX export includes the same column
- [x] Secondary sortable `engagement_rate = (likes + comments) / followers` column (cross-account comparison; separate from the badge, requires E5-S4)
- [x] A short inline tooltip or docs/UI_GUIDELINES.md note clarifies the badge is relative to *that account's own* baseline, not an absolute/industry benchmark — avoids it being misread (did both: a native `title` tooltip on the badge, plus a UI_GUIDELINES.md paragraph)
- [x] Unit tests: ratio computation against a fixed fixture (known likes/comments/views per account), threshold bucketing, insufficient-sample guard, reel `max(engagement_ratio, view_ratio)` combination
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (13 pure-Python tests in `test_metrics.py` — 8 `bucket_virality` threshold tests + 5 `virality_ratio` computation tests against fixed fixtures, all ran locally without a DB; a full-stack `test_virality_badge_and_engagement_rate` API test with a real median/outlier fixture and an insufficient-items account; `test_export.py` header/value assertions updated; mypy + ruff + `tsc --noEmit` + `next lint` all clean — and this time CI is actually green, see Changelog)
- [x] CI green, deployed to DEV
- [ ] Smoke test — DEFERRED (requires a real finished DEV run with a mixed-type account; same deferral pattern as every Apify-touching story)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On DEV, open a finished run with a mixed-type account (≥3 items) — badges show plausible High/Medium/Low; an account with <3 items shows no badge; sorting by `engagement_rate` works; export to Excel and confirm both columns are present.
### Files to read
CLAUDE.md, backend/src/services/metrics.py, backend/src/api/items.py, docs/UI_GUIDELINES.md, frontend/components/results-table.tsx
### Files to create or modify
backend/src/services/metrics.py, backend/src/config.py, backend/src/api/items.py, backend/tests/test_items_api.py, frontend/components/results-table.tsx, frontend/messages/ru.json, backend/src/services/xlsx_export.py, backend/tests/test_export.py
### Changelog
- Thresholds/insufficient-sample bucketing is a pure Python function (`metrics.py:bucket_virality(ratio, item_count, settings)`) rather than SQL `CASE` logic, specifically so it's unit-testable without a database — the AC's "threshold bucketing, insufficient-sample guard" tests run fully offline in `test_metrics.py`.
- **CI-breaking bug found post-push, fixed same day (2026-07-22):** the first version computed the per-account median via a SQL window function — `percentile_cont(0.5).within_group(engagement).over(partition_by=account_id)`. This is invalid: Postgres does not support `OVER` for ordered-set aggregates like `percentile_cont` (`ERROR: OVER is not supported for ordered-set aggregate percentile_cont`), only plain `GROUP BY` aggregation — a real gap in local verification, since there was no Postgres available in this sandbox to catch it before CI did. Fixed by replacing the window function with `virality_baseline_subquery(run_id)`: a proper `GROUP BY account_id` subquery (`median_engagement`, `median_views`, `item_count` per account) joined onto the item query by `account_id`. The ratio math itself (`engagement/median`, `views/median_views`, taking the higher of the two) moved out of SQL entirely into a second pure Python function, `virality_ratio()` — which turned out to be a strict improvement, not just a workaround: it let the AC's "ratio computation against a fixed fixture" unit tests run fully offline too, alongside the bucketing tests, instead of needing a live DB.
- `NULLIF`/`or None` guards used everywhere a ratio divides by a per-account median, so an all-zero-engagement account produces a `None` ratio (routed into "no badge") instead of a division-by-zero crash or a fabricated infinite ratio.
- `max()` over only the non-None candidates (`virality_ratio()`) replaces the earlier `GREATEST(...)` SQL call — same NULL-safe "ignore missing components" behavior, now in Python: a non-reel item's `view_ratio` is always `None`, so it cleanly falls back to `engagement_ratio` alone.
- Extra file touched beyond the story's list: `docs/UI_GUIDELINES.md`'s "Results table" section had drifted (still listed a Просмотры column removed in an earlier UI pass, no mention of followers/comments from this sprint's earlier stories) — updated it to match current reality while adding the required self-relative clarification, rather than leaving a second stale spot next to a freshly-accurate one.
- Badge styling didn't reuse the shared `Badge` component (`components/ui/index.tsx`) — its 4 variants (default/success/warning/danger) don't cleanly express "success / neutral / muted" without stretching a variant's meaning, so the three states are small inline-styled chips directly in `results-table.tsx`, matching how the existing "type" column already does its own inline chip.
### Handover
- `backend/src/services/metrics.py`: `virality_baseline_subquery(run_id)` (SQL, `GROUP BY account_id` — **not** a window function, see Changelog), `virality_ratio(likes, comments, views, median_engagement, median_views)` (pure Python), `engagement_rate_expr()` (SQL, per-row, needs `Account` joined), `bucket_virality(ratio, item_count, settings)` (pure Python). Only the median/count aggregation itself touches the DB; ratio computation and bucketing are both unit-testable offline.
- `Settings.virality_high_ratio` (2.0), `virality_low_ratio` (0.7), `virality_min_items` (3) — tunable without a code change, same pattern as `estimator.py`.
- `ContentItemOut.virality: Literal["high","medium","low"] | None` and `.engagement_rate: float | None` — both `api/items.py` and `api/export.py` build the subquery, join it by `account_id`, and call `bucket_virality(virality_ratio(...), item_count, settings)` per row identically; copy this pattern if a third read-path is ever added.
- `xlsx_export.py`: "Виральность" (column 14) is the Russian bucket label or blank; "Вовлечённость" (column 15) is the raw fraction with `number_format = "0.0%"` applied per-cell so Excel renders it as a percentage while keeping it numeric/sortable.
- Frontend: `results-table.tsx` — `formatPercent()`, `VIRALITY_STYLE` (Tailwind classes per bucket), `VIRALITY_LABEL` (i18n, built inside the component since it needs `t()`). Badge cell has a `title` tooltip; `docs/UI_GUIDELINES.md` carries the same self-relative clarification for anyone not hovering.
- **Lesson for future read-time-metric stories:** Postgres ordered-set aggregates (`percentile_cont`, `percentile_disc`, `mode`) never support `OVER` — if a per-group statistic more exotic than `SUM`/`COUNT`/`AVG` is needed per-row (not collapsed by `GROUP BY`), the answer is a `GROUP BY` subquery joined back by the grouping key, not a window function. Worth a quick doubt-check against Postgres docs before assuming a window-function equivalent exists for a given aggregate, in a sandbox without a live DB to catch it early.
- This closes out Sprint 7 (SPRINT.md) — every story from the 2026-07-21 reprioritization is now done and CI-green. Next planning step is a `/sprint-review` to pick Sprint 8, per BACKLOG.md's "Post-MVP (not yet ordered)" list (E3-S3/S4, E3-S5, E7-S3, E8-S3/S4, E9/E10/E11).

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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Status:** done
**Completed:** 2026-07-19
**Priority:** high
**Depends on:** E1-S3
### Goal
Users can log in via Telegram (Login Widget on web), as a second `AuthProvider` alongside email+password, ahead of VK ID in priority (D18).
### Acceptance Criteria
- [x] `TelegramAuthProvider` verifies the Telegram Login Widget payload (hash check against bot token) and issues the same JWT as email+password login
- [x] First-time Telegram login creates a user + personal workspace, same as registration; existing email-user can link a Telegram account from settings (backend endpoint `POST /auth/telegram/link`; settings UI in E8-S2)
- [x] Login page offers «Войти через Telegram» alongside email+password
- [x] No changes required to any call site consuming the auth dependency (interface from E1-S3 holds)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test — DEFERRED (requires TELEGRAM_BOT_TOKEN + TELEGRAM_BOT_USERNAME on Railway DEV)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On DEV, log in with a real Telegram account via the widget — lands in an authenticated workspace.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (Auth, Telegram Mini App sections), backend/src/auth/*.py
### Files to create or modify
backend/src/auth/telegram.py, backend/tests/test_telegram_auth.py, frontend/app/(auth)/login/page.tsx, frontend/messages/ru.json
### Handover
- `backend/src/auth/telegram.py`: `verify_login_widget(data, bot_token)`, `verify_webapp_init_data(init_data, bot_token)`, `find_or_create_telegram_user(session, telegram_id)`
- `POST /auth/telegram/login` — Login Widget; `POST /auth/telegram/webapp` — Mini App initData; `POST /auth/telegram/link` — link TG to existing email account (auth required)
- `GET /auth/telegram/config` — returns `{enabled, bot_username}` for frontend widget conditional
- `users.telegram_id` (BigInteger, unique, nullable) — migration `f1a2b3c4d5e6`
- ENV: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` on api (both required for Telegram auth to activate)
- 8 unit tests in `test_telegram_auth.py`; 5 integration tests in `test_telegram_webapp.py` (run in CI against test DB)

## [E8-S2] Telegram bot notifications
**Epic:** Telegram Integration & Monetization
**Sprint:** 6 (stretch — do last, skip if the sprint runs long)
**Status:** done
**Completed:** 2026-07-19
**Priority:** medium
**Depends on:** E8-S1, E3-S1
### Goal
A user with a linked Telegram account gets a bot message when their analysis run finishes, with a deep link back into the results.
### Acceptance Criteria
- [x] Backend sends a message via Bot API on run `done`/`failed` to users with a linked `telegram_id` (serves as chat_id for private DMs)
- [x] Message text in Russian; includes item count and a web URL deep link for done; error snippet for failed
- [x] Users without a linked account are unaffected (no error, just skipped)
- [x] Notification send failure never fails the run (try/except → logger.warning)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test — DEFERRED (requires bot token + linked account on DEV; unblocked once E8-S1/S5 human prerequisites met)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Link Telegram on DEV, start a run, get a bot DM when it completes.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/auth/telegram.py
### Files to create or modify
backend/src/services/telegram_notify.py, backend/src/worker.py, backend/tests/test_telegram_notify.py, frontend/app/(app)/settings/**, frontend/messages/ru.json
### Handover
- `backend/src/services/telegram_notify.py`: `notify_run_complete(run, user)` — sends Bot API DM; skips if no bot token or no telegram_id; never raises
- `worker.py`: calls `notify_run_complete` after done commit and inside both except branches (CancelledError + generic Exception)
- `UserOut` (backend) + `UserResponse` (frontend) now expose `has_telegram: bool`
- `POST /auth/telegram/link` (E8-S1) + Settings page `/settings` — Telegram Login Widget to link an email account to TG; `has_telegram` state updates on success
- App header: «Настройки» link added
- 5 unit tests in `test_telegram_notify.py` (mocked httpx; no DB required)

## [E8-S3] Telegram Stars subscriptions
**Epic:** Telegram Integration & Monetization
**Sprint:** 10 (locked 2026-07-22 execution plan — after E13/E14/E15/E16 land so the subscription entry point has a UI home)
**Status:** backlog
**Priority:** high
**Depends on:** E8-S5, E7-S1, E13-S1 (nav restructure — subscription screen is reached from a profile/settings entry point, not the 3-tab bottom nav)
### Goal
Users subscribe to a usage plan paid in Telegram Stars inside the Mini App. The Mini App shell itself (initData auth, bot entry point) ships earlier in E8-S5 — this story is billing only.

**Re-scoped 2026-07-22 per D30:** launch is a **single tier** — 1990 ₽/month → 2000 tokens, credited onto the existing `User.token_balance` int column (already live and already gating runs, see `backend/src/api/runs.py`'s `NO_BALANCE` check and `backend/src/worker.py`'s balance debit) — not D26's full multi-tier X-factor pricing config, which remains a later extension.
### Acceptance Criteria
- [ ] Recurring Telegram Stars subscription invoice (Bot API subscription support) for the single 1990₽-equivalent/2000-token plan; `POST` flow creates the invoice, confirmed via Bot API successful-payment webhook; new `subscriptions` table (user_id, status, current_period_end, telegram_charge_id)
- [ ] Each successful billing cycle credits `token_balance += 2000` (reuses the existing column — no new ledger)
- [ ] «Использование»/subscription screen shows current balance, price ("≈1990 ₽/мес"), and a subscribe button opening Telegram's native invoice sheet
- [ ] The existing `insufficient_token_balance` run-creation error links to this subscription screen instead of a dead end
- [ ] Mini App respects D16 (usable at Telegram's in-app viewport sizes) and D20 (loads whatever domain/proxy stage is currently active — no Mini-App-specific network path)
- [ ] D26's internal `usage_events` cost ledger is untouched by this story — it stays layer-1 only; no X-factor/internal-cost value is introduced or exposed
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Open the Mini App from the bot on DEV, subscribe with test Stars, confirm `token_balance` increases by 2000 and a previously blocked run unblocks after payment.
### Files to read
CLAUDE.md, DECISIONS.md (D19, D26, D30), docs/ARCHITECTURE.md (Telegram Mini App, Usage Metering sections), backend/src/api/usage.py, backend/src/api/runs.py, backend/src/auth/telegram.py
### Files to create or modify
backend/src/api/billing.py, backend/src/models/subscription.py, backend/tests/test_billing.py, frontend/app/(app)/**, frontend/lib/telegram-webapp.ts, frontend/messages/ru.json
### Handover
—

## [E8-S4] Add competitor by sharing a link to the bot
**Epic:** Telegram Integration & Monetization
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Status:** done
**Completed:** 2026-07-19
**Priority:** critical
**Depends on:** E8-S1, E12-S2
### Goal
The app opens inside Telegram from the bot with zero login friction, so it can be shared with test users by bot handle (D27). This is the Sprint 6 exit criterion. Payments are explicitly out of scope (they stay in E8-S3, post-Sprint-6) — hard constraint: no billing/Stars code in this story.
### Acceptance Criteria
- [x] Minimal bot webhook on the api service (`POST /telegram/webhook`, validated via `X-Telegram-Bot-Api-Secret-Token` against `TELEGRAM_WEBHOOK_SECRET`): `/start` replies in Russian with an inline «Открыть content-scout» `web_app` button pointing at the web URL. Webhook + chat menu button (`setChatMenuButton`) registered via Bot API from a small idempotent setup path — no BotFather steps needed beyond bot creation
- [x] Bot API called with plain `httpx` (no bot-framework dependency, D27)
- [x] Frontend detects Telegram context (`window.Telegram.WebApp` with non-empty `initData`), sends `initData` to `POST /auth/telegram/webapp`; backend verifies the HMAC per Telegram Web App spec (secret key = HMAC-SHA256 of bot token with "WebAppData", `auth_date` ≤ 24h old) and returns the standard JWT; first open auto-creates user + personal workspace via `TelegramAuthProvider` (E8-S1)
- [x] Inside Telegram: no login/register forms ever shown, logout hidden, `Telegram.WebApp.ready()` + `expand()` called; bottom navigation (E12-S2) and safe-area behave correctly in the webview
- [x] Outside Telegram the web app behaves exactly as before (auth flow untouched)
- [ ] Works on DEV over the public Railway HTTPS URL — DEFERRED (requires TELEGRAM_BOT_TOKEN + TELEGRAM_WEBHOOK_SECRET + WEB_URL on Railway DEV)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test — DEFERRED (human prerequisites: create bot via @BotFather, set env vars on Railway DEV)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
From a phone: open the DEV bot, tap «Открыть content-scout» — the Mini App opens already authenticated, workspace auto-created; full flow (create project → add competitors → run → browse card results → shortlist) works inside Telegram. Repeat from a second Telegram account to confirm it is shareable.
### Files to read
CLAUDE.md, DECISIONS.md (D17, D27), docs/ARCHITECTURE.md (Telegram Mini App section), backend/src/auth/telegram.py, frontend/lib/auth-context.tsx
### Files to create or modify
backend/src/api/telegram_webhook.py, backend/src/auth/telegram.py, backend/src/config.py, backend/src/main.py, backend/tests/test_telegram_webapp.py, frontend/lib/telegram-webapp.ts, frontend/lib/auth-context.tsx, frontend/app/layout.tsx, frontend/messages/ru.json, ENV.md
### Handover
- `backend/src/api/telegram_webhook.py`: `POST /telegram/webhook` (HMAC-validated); `setup_webhook_and_menu()` called at startup via FastAPI lifespan; uses `RAILWAY_PUBLIC_DOMAIN` env to self-discover API URL
- `frontend/lib/telegram-webapp.ts`: `isTelegramContext()`, `getTelegramInitData()`, `initTelegramWebApp()` (ready + expand)
- `auth-context.tsx`: `isTelegram` exposed in context; auto-auth via initData on first load if no stored JWT
- `app/(app)/layout.tsx`: logout + email hidden when `isTelegram`; login page returns `null` when `isTelegram`
- ENV added: `TELEGRAM_WEBHOOK_SECRET` (api), `TELEGRAM_BOT_USERNAME` (api), `WEB_URL` (api — Mini App URL sent in bot messages)

## [E8-S6] Telegram Mini App auto-login bootstrap fix
**Epic:** Telegram Integration & Monetization
**Sprint:** unassigned (MVP — next up; live-blocking bug for the single-blogger pilot, found + root-caused during 2026-07-21 sprint review)
**Status:** done
**Completed:** 2026-07-22
**Priority:** critical
**Depends on:** E8-S1, E8-S5
### Goal
Confirmed 2026-07-21: the web Login Widget flow (`/login`, `/setdomain` registered) works correctly — the 7 untracked `fix:` commits since E8-S1 shipped (`53b2fac`..`02f725c`) were legitimate fixes to that flow, just never tagged to a story. The actual live bug is the **Mini App** (opened via the bot's «Открыть» button), which has been non-functional since E8-S5 shipped.
Root cause: Telegram does **not** auto-inject `window.Telegram.WebApp` into the Mini App webview — the page must load Telegram's own SDK script (`telegram-web-app.js`) itself to get it populated. This codebase only ever loaded `telegram-widget.js` (the unrelated Login *Widget* script, used on `/login`/`/register`/`/settings`); the Mini App SDK script was never included anywhere. So `isTelegramContext()` ([telegram-webapp.ts:15](frontend/lib/telegram-webapp.ts:15)) always returned `false` even inside the real Mini App, the auto-login branch in [auth-context.tsx:51](frontend/lib/auth-context.tsx:51) never ran, and the user saw the ordinary email/password login form instead of silent auto-auth.
### Acceptance Criteria
- [x] Load `https://telegram.org/js/telegram-web-app.js` via `next/script` (`strategy="beforeInteractive"`) in the root layout, so `window.Telegram.WebApp` exists before `AuthProvider`'s mount effect runs
- [x] `suppressHydrationWarning` added to `<html>` — Telegram's script mutates `document.documentElement.style` (`--tg-viewport-height` custom properties) as a side effect of loading even outside real Telegram, causing an SSR/client hydration mismatch on `<html>`'s attributes; this is expected third-party-script behavior, not a bug to chase
- [x] **End-to-end smoke test with a real Telegram account against DEV** — confirmed live: user opened the Mini App from the bot on a real phone and drove an extended real session (account menu, run dialog, competitor list) without ever seeing a login form, reporting only UI/UX bugs downstream of a successfully authenticated session. Auto-login works.
- [x] If the real-device test still fails after this fix, root-cause from actual console/network output against DEV rather than another speculative patch — not needed, fix held on first real-device pass
### Definition of Done
- [x] All AC checked
- [x] Local verification: outside real Telegram, `window.Telegram.WebApp.initData` is `""` (confirmed via browser JS eval) so `isTelegramContext()` still correctly returns `false` for normal browser sessions — no regression to non-Telegram login; typecheck + lint clean
- [x] Smoke test passed (real Telegram account, not deferred) — see Changelog
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
From a real phone, open the DEV bot and tap «Открыть content-scout» — the Mini App opens already authenticated (no login form), workspace loads directly.
### Files to read
CLAUDE.md, frontend/app/layout.tsx, frontend/lib/telegram-webapp.ts, frontend/lib/auth-context.tsx
### Files to create or modify
frontend/app/layout.tsx (done)
### Changelog
- 2026-07-21: root cause fixed — `telegram-web-app.js` script added to root layout via `next/script`. Verified locally (typecheck, lint, browser check of `isTelegramContext()` behavior).
- 2026-07-21/22: real-device smoke test confirmed live — user drove an extended session inside the actual Mini App (account menu, non-blocking run dialog, competitor selection) with zero manual login, reporting five follow-up UI bugs against an already-authenticated session (no exit affordance, no display name shown, modal-blocking on run start, missing spacing on project creation, redundant competitor counters) plus a separate Apify `max_total_charge_usd` production incident (stuck runs). All fixed same-session in a series of untracked `fix:`/`feat:` commits (`e20e5ed`, `0055313`, `07c2b9a`, `e8dbae8`) — see DONE.md for the consolidated writeup, since these were direct bug-report fixes rather than pre-planned AC and don't warrant separate backlog stories.
### Handover
- `frontend/app/layout.tsx` loads `telegram-web-app.js` via `next/script` `beforeInteractive` — required for any future Mini-App-only feature to rely on `window.Telegram.WebApp` being populated on first paint.
- Session also added, on top of the bootstrap fix itself: `users.display_name` (editable in Settings, random default on registration — migration `c2275f27bb18`), a global `RunTrackerProvider` (`frontend/lib/run-tracker.tsx`) so the run dialog is closable/minimizable and multiple runs can be tracked in parallel with a header notification bell, a "soft logout" flow for the Mini App (`telegramLogout()` + `content-scout-tg-logged-out` localStorage flag, since Telegram itself has no real sign-out), and an Apify `max_total_charge_usd` cap (`Settings.apify_max_charge_per_fetch_usd`, default $0.5) to stop concurrent runs from deadlocking on Apify's Pay-Per-Event implicit balance reservation.
- None of this is scheduled backlog work — it's what the first real-device pilot session surfaced. Flagging here since it changed several files future stories in this sprint will also touch: `frontend/app/(app)/layout.tsx`, `frontend/app/(auth)/login/page.tsx`, `backend/src/platforms/instagram.py`.
—

## [E9-S1] Public API tokens
**Epic:** Public API & Engine Integration
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Sprint:** unassigned (post-MVP per 2026-07-21 reprioritization — single-blogger focus)
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
**Status:** done
**Completed:** 2026-07-19
**Priority:** high
**Depends on:** E6-S2
### Goal
The product stops looking like a wireframe: the light design system approved in the 2026-07-18 UI review (D28) — violet accent, tinted background with white cards, Cyrillic-first fonts, real icons — is applied to every existing screen. Dark mode is removed entirely.
### Acceptance Criteria
- [x] Design tokens defined once in `globals.css` (Tailwind v4 `@theme`): background `#F6F7F9`, card `#FFFFFF`, ink `#1A1523`, secondary text `#6F6E77`, accent `#6E56CF` (hover ~`#5D48B8`), accent-soft `#EDE9FE`, success `#30A46C` (soft `#E9F9F1`), star/warning `#FFB224`, danger `#E5484D`, hairline border `#E4E2E9`; radius: cards 14px, controls 12px, chips 999px. All components consume tokens — no ad-hoc hex in components
- [x] Fonts via `next/font/google`: **Golos Text** (UI + data, tabular figures for metric columns), **Unbounded** (logo/display accents only); zero layout shift
- [x] `lucide-react` replaces every emoji/unicode glyph used as an icon (⊞ ★ ☆ ✕ ▲ ▼ 🎬 🖼️) — D28 dependency entry
- [x] Shared primitives in `frontend/components/ui/index.tsx`: Button (primary/secondary/ghost/danger), Card, Input, Textarea, Badge — created; screens use token classes directly (consistent with CONVENTIONS.md inline Tailwind pattern)
- [x] Dark mode removed: every `dark:` class deleted (grep confirms zero), `<html>`/body backgrounds set to `bg-bg` token; app stays light regardless of OS theme
- [x] All existing screens re-skinned (login/register, projects home, project tabs: competitors/results/shortlist/history, usage, admin, run dialog); verified at 375px and 1280px in browser, no layout regressions
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (no new test surface — purely visual; typecheck passes)
- [x] CI green, deployed to DEV
- [x] Smoke test passed
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
DEFERRED — requires DEV deploy (push to main triggered CI deploy; can be smoke tested on https://web-dev-99e3.up.railway.app once CI completes). Local browser verification at 375px and 1280px PASSED: violet accent, white cards on tinted background, Golos Text Cyrillic font, Unbounded logo, lucide icons replacing all emoji, zero dark surfaces.
### Files to read
CLAUDE.md, DECISIONS.md (D28), docs/UI_GUIDELINES.md, frontend/app/globals.css, frontend/app/layout.tsx
### Files to create or modify
frontend/app/globals.css, frontend/app/layout.tsx, frontend/components/ui/index.tsx (new), frontend/components/results-table.tsx, all files under frontend/app/(auth)/** and frontend/app/(app)/**, frontend/package.json (lucide-react)
### Handover
- `frontend/app/globals.css` — all D28 design tokens as Tailwind v4 `@theme` variables; use `bg-bg`, `bg-card`, `bg-accent`, `text-ink`, `text-secondary`, `text-accent`, `text-danger`, `text-success`, `text-warning`, `border-border`, `rounded-card`, `rounded-control`, `rounded-chip`, `font-sans`, `font-display`
- `frontend/components/ui/index.tsx` — Button, Card, Input, Textarea, Badge primitives (thin Tailwind wrappers)
- `lucide-react` ^1.25.0 — Film, ImageIcon, Images, Star, ChevronUp/Down, Maximize2, X used in results-table and shortlist/history pages
- All screens: zero `dark:` classes, zero emoji glyphs as icons

## [E12-S2] Mobile cards, bottom navigation, UX states
**Epic:** UI/UX Modernization
**Sprint:** 6
**Status:** done
**Completed:** 2026-07-19
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
- `frontend/components/results-cards.tsx` — `ResultsCards` (cards + SortBottomSheet) and `ShortlistCards` for mobile views
- `frontend/components/ui/skeleton.tsx` — `SkeletonLine`, `SkeletonCard`, `SkeletonList`, `SkeletonRow`, `SkeletonRows`
- `frontend/components/ui/toast.tsx` — `ToastProvider` (root layout), `useToast()` hook with `addToast(msg, variant)`
- `frontend/components/ui/bottom-nav.tsx` — `ProjectBottomNav` (md:hidden, safe-area-inset-bottom, ≥44px); in project layout
- All list screens — skeleton loaders, errors → toasts, designed empty states (FolderOpen/Users icons)
- Results/shortlist — cards at <768px, table at ≥768px
- `ru.json` — `ResultsCards` namespace; `Projects.emptyHint`

## [E12-S3] Mobile results controls consolidation + polish
**Epic:** UI/UX Modernization
**Sprint:** 7 (untracked — shipped 2026-07-22 as direct fixes/polish during the Sprint 7 session, backfilled here per the sprint-review "untracked fixes" check)
**Status:** done
**Completed:** 2026-07-22
**Priority:** medium
**Depends on:** E12-S2, E5-S5 (virality badges), E5-S3 (comments column)
### Goal
Three separate rows of mobile results controls (run-selector, token-warning, sort+export) collapse into one icon row, and a batch of related UX polish lands: virality badge colors that read correctly against the design system, less visual noise on collapsed cards, and new sort options for the metrics added in E5-S3/E5-S5.
### Acceptance Criteria
- [x] Single icon row: sort (bottom sheet, active option emphasized), export (bottom sheet with export button + explanatory copy — includes the Telegram-downloads-folder note when `canDownloadViaTelegram()`), run-filter (bottom sheet listing runs + "все запуски"), star (shows only shortlisted items, respecting the active run filter)
- [x] Sort/filter/star grouped left; export icon pushed right (`ml-auto`)
- [x] Все/Отмеченные tabs removed — the star filter supersedes them
- [x] Virality badges: medium → soft yellow, low → soft red (previously both grey, indistinguishable from other chips); high stays green
- [x] Days-since-publication chip hidden on collapsed cards, shown only when a card is expanded
- [x] New sort options: virality (new SQL-level `virality_ratio_expr`, since the badge itself is only bucketed), engagement rate, comments
- [x] Export always exports exactly the currently filtered/visible list
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — DEFERRED (same pattern as the rest of Sprint 7; needs a real finished DEV run to eyeball on a phone)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On a phone/Telegram webview at 375px, open Результаты for a project with a finished run: confirm the single control row, sort by each new option, star-filter with and without a run selected, export and confirm the file matches the visible filter.
### Files to read
CLAUDE.md, DECISIONS.md (D28), frontend/components/results-cards.tsx, frontend/lib/format.ts
### Files to create or modify
frontend/components/results-controls.tsx (new), frontend/app/(app)/projects/[id]/results/page.tsx, frontend/components/results-cards.tsx, frontend/lib/format.ts, frontend/lib/api.ts, backend/src/services/metrics.py (`virality_ratio_expr`), backend/src/api/items.py, backend/src/api/export.py, frontend/messages/ru.json
### Handover
- `frontend/components/results-controls.tsx` — new single-row control bar (`SORT_FIELDS`/`SORT_LABELS` include `virality`, `engagement_rate`, `comments`); replaces the old inline tab/sort/export/run-filter markup that used to live directly in `results/page.tsx`.
- `backend/src/services/metrics.py:virality_ratio_expr(median_engagement, median_views, item_count, settings)` — SQL-level version of the existing Python `bucket_virality` ratio, wired into the `sort_columns` dict in both `api/items.py` and `api/export.py` (paginated + full-run export).
- `frontend/lib/format.ts:VIRALITY_STYLE` — `medium: "bg-warning/10 text-warning"`, `low: "bg-danger/10 text-danger"` (both were grey before).
- Orphaned `/projects/[id]/shortlist/page.tsx` was flagged (not fixed) as dead code once the tabs were removed — separate cleanup task, not done here.
- Commits: `b955fba` (single-row collapse), `9468564` + `7679080` (tabs removal, colors, sort options, export copy — the second commit fixed a CI-only constraint-name test mismatch, unrelated to this story's own logic).

## [E3-S7] Run scope: last-N-publications mode
**Epic:** Analysis Pipeline
**Sprint:** 7 (untracked — shipped 2026-07-22 alongside E12-S3, backfilled here)
**Status:** done
**Completed:** 2026-07-22
**Priority:** medium
**Depends on:** E3-S1, E3-S2
### Goal
Alongside the existing "last N days" run window, a user can instead scope a run to "last N publications per account" (5–50) — useful for low-frequency posters where a day window returns too little, or high-frequency posters where it returns too much.
### Acceptance Criteria
- [x] `AnalysisRun.duration_days` and `.item_limit` are both nullable; exactly one is set, enforced by a Postgres CHECK constraint (`duration_or_item_limit_range`)
- [x] Run-creation dialog gets a day-window/count segmented toggle; count mode offers 5/10/15/20/30/50
- [x] Estimator (`estimate_run`) branches: `accounts_count × item_limit` in count mode vs. the existing duration-based calc
- [x] `Platform.fetch_content` takes keyword-only `since: datetime | None` + `limit: int | None`; Instagram scraper omits `onlyPostsNewerThan` and uses `resultsLimit` directly in count mode; `MockPlatform` mirrors the branching
- [x] History/run-summary views render whichever of the two is set ("N дней" / "последние N публикаций")
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — DEFERRED (needs a real DEV run in count mode against public IG accounts)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On DEV, start a run in "last N publications" mode against a low-frequency account; confirm the worker fetches exactly N items per account regardless of how old they are, and History shows "последние N публикаций" for that run.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (run lifecycle), backend/src/models/analysis_run.py, backend/src/platforms/base.py
### Files to create or modify
backend/src/models/analysis_run.py, backend/alembic/versions/b8c4d5e6f7a1_run_item_limit.py (new), backend/src/services/estimator.py, backend/src/api/runs.py, backend/src/api/usage.py, backend/src/platforms/base.py, backend/src/platforms/instagram.py, backend/src/platforms/mock.py, backend/src/worker.py, frontend/app/(app)/projects/[id]/run-dialog.tsx, frontend/app/(app)/projects/[id]/history/page.tsx, frontend/lib/api.ts, frontend/messages/ru.json
### Handover
- Migration `b8c4d5e6f7a1` is head; downgrade backfills `duration_days=7` before restoring the old NOT NULL.
- Found and fixed a real bug in passing: `RunSummaryOut` in `api/usage.py` had `duration_days: int` (non-optional) — would have 500'd on any item_limit-mode run. Now `int | None` + `item_limit: int | None`.
- `RunRequestIn` uses a `model_validator(mode="after")` to enforce exactly-one-of at the API layer, mirroring the DB constraint.
- Commit: `9468564` (shipped together with E12-S3's frontend polish in the same push), fixed up in `7679080` after CI caught a stale constraint-name assertion in `test_run_duration_check_rejected`.

## [E13-S1] Bottom nav restructure: Детали / Результаты / Анализ
**Epic:** Navigation & Details Restructure
**Sprint:** 8 (locked 2026-07-22 execution plan)
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** none
### Goal
The project bottom nav (and desktop tab bar) collapses from the current Конкуренты/Результаты/Создать to exactly three items: **Детали**, **Результаты**, **Анализ**. Детали becomes the project's landing page; Конкуренты and Создать stop being top-level tabs and move behind Детали (E13-S2, E13-S3, E16-S1).
### Acceptance Criteria
- [x] `ProjectBottomNav` and the desktop tab bar in `layout.tsx` both show exactly Детали/Результаты/Анализ, in that order
- [x] Root project route (`/projects/[id]`) redirects to `/projects/[id]/details` instead of `/competitors`
- [x] `/projects/[id]/create` route removed (superseded by Детали's inline create-run entry point, E13-S2, and by E16-S1's Анализ teaser)
- [x] `sectionHeading()` in the shared layout recognizes the new `/details` and `/analysis` segments
- [x] Existing deep links to `/results?run=...` (used by Telegram notifications, E15-S3) keep working unchanged
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (no frontend unit test suite in this repo — CI gate is typecheck + eslint per CONVENTIONS.md, both green; nothing here warrants a new component test)
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — deferred, see below
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Open a project on DEV at both desktop and 375px — bottom/tab nav shows only the three new items, landing on Детали; old `/competitors` and `/create` links redirect or 404 gracefully.
**DEFERRED** — verified locally instead via a temporary scratch route (`frontend/app/dev-preview/nav`, mounted the real `ProjectBottomNav` + tab bar with mock props, screenshotted at desktop and 375px, then deleted before commit) since no local Postgres/DEV login is available in this sandbox — same pattern as E12-S3.
### Files to read
CLAUDE.md, DECISIONS.md (D28), frontend/components/ui/bottom-nav.tsx, frontend/app/(app)/projects/[id]/layout.tsx, frontend/app/(app)/projects/[id]/page.tsx
### Files to create or modify
frontend/components/ui/bottom-nav.tsx, frontend/app/(app)/projects/[id]/layout.tsx, frontend/app/(app)/projects/[id]/page.tsx, frontend/messages/ru.json
### Handover
- `frontend/app/(app)/projects/[id]/create/` deleted; new stub routes `frontend/app/(app)/projects/[id]/analysis/page.tsx` (Sparkles "coming soon" pattern, `Analysis` message namespace — E16-S1 will replace with the real teaser cards) and `frontend/app/(app)/projects/[id]/details/page.tsx` (bare placeholder, `Details` message namespace — E13-S2 replaces with the full dashboard).
- `ProjectShell` messages: added `sectionDetails`/`sectionAnalysis`/`tabDetails`/`tabAnalysis`; `tabResults` now correctly says "Результаты" (previously mislabeled "Анализ" while pointing at the results segment — fixed as part of this restructure). Removed `sectionCreate`/`Create` namespace (dead after `/create` removal).
- `/history` route and its message namespace are untouched — not in this story's file list; E13-S2 builds its own run-history cards rather than reusing that page.
- No backend changes.

## [E13-S2] Details dashboard: KPI card, nav links, run-history cards, create-run entry
**Epic:** Navigation & Details Restructure
**Sprint:** 8
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E13-S1
### Goal
Детали becomes the project's real landing page: a project-level KPI summary, full-width links into Competitors and Scheduled Runs, a card-based run history (replacing the run table currently on `/history`), and the entry point for creating a new run.
### Acceptance Criteria
- [x] Dashboard card: number of competitors, total publications analyzed since project start (new lifetime aggregate — not scoped to one run); card is built to take more KPIs later without a layout rewrite
- [x] Full-width "Конкуренты" button (arrow-right, right-aligned, same visual style as a competitor row) → `/projects/[id]/competitors`
- [x] Full-width "Запланированные запуски" button, same style → `/projects/[id]/scheduled` (E14-S3)
- [x] Run history as cards (not the old table): date, accounts analyzed, publications analyzed, tokens consumed per run; tapping a card opens the run detail view (E15-S3)
- [x] "Создать запуск" button opens the existing run-creation flow (extended in E14-S4 with a Run-now/Schedule choice)
- [x] New backend aggregate endpoint (or extension of an existing one) for the lifetime publications-analyzed count, scoped to the caller's own project (reuses `get_owned_project`)
- [x] Screen usable at 375px (D16); cards, not the old table, at every width for this list specifically (this is a dashboard, not a data table)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (`test_project_stats_sums_items_across_runs`, `test_project_stats_zero_with_no_runs`, `test_project_stats_scoped_to_workspace` in `test_projects.py`; ruff/mypy clean locally, pytest needs the CI Postgres service — no local DB in this sandbox)
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — deferred, see below
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Open Детали on DEV for a project with at least one finished run — KPI card shows correct counts, both nav buttons navigate correctly, run cards show plausible data and open the right run.
**DEFERRED** — verified locally instead via a temporary `frontend/app/dev-preview/details` scratch route (real component structure, mock accounts/stats/runs data), screenshotted at desktop and 375px, then deleted before commit — same pattern as E12-S3/E13-S1. No local Postgres/DEV login available in this sandbox to exercise the real endpoints end-to-end.
### Files to read
CLAUDE.md, DECISIONS.md (D16, D28), docs/UI_GUIDELINES.md, backend/src/api/usage.py (existing run-summary shape), frontend/app/(app)/projects/[id]/history/page.tsx (run table being replaced)
### Files to create or modify
frontend/app/(app)/projects/[id]/details/page.tsx (new), backend/src/api/projects.py or usage.py (lifetime aggregate), frontend/lib/api.ts, frontend/messages/ru.json
### Handover
- `GET /projects/{project_id}/stats` (`backend/src/api/projects.py`) — `ProjectStatsOut.lifetime_items_analyzed`, `SUM(AnalysisRun.progress_items)` (`func.coalesce(..., 0)`) across every run for the project regardless of status, scoped via the existing `_get_owned_project`/`get_owned_project` 404-on-mismatch pattern. `frontend/lib/api.ts` gained `ProjectStatsResponse` + `api.getProjectStats`.
- "Tokens consumed" per run card reuses `run.progress_items` — this system debits exactly 1 token per scraped publication (see `worker.py`'s `token_balance -= len(batch)`), so publications-analyzed and tokens-consumed are the same underlying number by design, not two independently-tracked fields. No new backend field needed for it.
- `details/page.tsx` fetches `listAccounts` + `getProjectStats` + `listRuns` in parallel; competitor count comes from the existing accounts list (no new endpoint needed for that half of the KPI card). KPI card renders as a 2-column grid of `{value, label}` pairs — adding a third stat later is one more grid cell, no layout rewrite.
- "Запланированные запуски" links to `/projects/[id]/scheduled`, which doesn't exist yet (E14-S3, Sprint 9) — 404s until then, same forward-reference pattern the AC itself specifies.
- Run cards only navigate to `/results?run=<id>` when `status === "done"` (mirrors the old `/history` table's `openResults` gating); other statuses show an inline status label instead of being clickable, since the run-detail view itself doesn't exist until E15-S3.
- "Создать запуск" opens the existing `RunDialog` with `accountIds: undefined` (whole active list) — per-run competitor scoping is gone now that E13-S3 removes selection from the Competitors page; `accountsCount` comes from the same accounts fetch.
- `/history` route is still untouched (not in this story's file list) — its run table now duplicates what Детали shows, worth flagging as cleanup once E15-S3 exists and nothing links to `/history` anymore.
- New `Details` message namespace (KPI/nav/run-card/status strings) fully replaces the earlier placeholder key from E13-S1.
- **POST-CLOSE CORRECTION (2026-07-22, same-day):** per direct user feedback, the "Создать запуск" button and the run-history block described above have been **moved from Детали to Результаты** — Результаты is now the run-list landing page (was previously assumed to be the item table), and Детали keeps only the KPI card + Конкуренты/Запланированные запуски nav links. Run cards now navigate to `/projects/[id]/runs/[runId]` (not `/results?run=...`, which E15-S3 built in the meantime). See the E15-S3 handover below and DONE.md's "Results/Details landing-page swap" entry for the full picture.

## [E13-S3] Competitors page trim
**Epic:** Navigation & Details Restructure
**Sprint:** 8
**Status:** done
**Completed:** 2026-07-22
**Priority:** medium
**Depends on:** E13-S1
### Goal
The Competitors page stops being a run-creation surface (that moves to Детали, E13-S2/E14-S4) and becomes a pure competitor-list management screen, reachable only from Детали.
### Acceptance Criteria
- [x] Selection checkboxes and "select all" removed
- [x] "Запустить анализ" button removed (run creation lives on Детали now)
- [x] Back button to Детали added
- [x] Add-competitor flow and everything else (avatar/name/followers display from E2-S3, remove, 50-cap info popover) unchanged
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (no frontend unit test suite in this repo — CI gate is typecheck + eslint, both green; nothing here warrants a new component test)
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — deferred, see below
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Open Конкуренты from Детали on DEV — no checkboxes, no run button, back button returns to Детали, add/remove still works.
**DEFERRED** — verified locally via a temporary `frontend/app/dev-preview/competitors` scratch route (mock accounts, real row/back-button/add-button markup), screenshotted at 375px, then deleted before commit — same pattern as the rest of Sprint 8's frontend-only stories.
### Files to read
CLAUDE.md, frontend/app/(app)/projects/[id]/competitors/page.tsx
### Files to create or modify
frontend/app/(app)/projects/[id]/competitors/page.tsx, frontend/messages/ru.json
### Handover
- `selected`/`runDialogOpen` state, `toggleSelected`/`toggleSelectAll`, the select-all header row, per-row checkboxes, and the `RunDialog` import/render all removed. `useProject()` now only destructures `isArchived` (the `project` value it also exposed was only needed for the removed `RunDialog`).
- Added a "← Детали" back link (`ArrowLeft` icon) at the top of the page, linking to `/projects/[id]/details`.
- `Competitors.infoExplanation` (the 50-cap info popover copy) rewritten — the old text referenced selecting accounts and running analysis, both gone from this page now. `runButton`/`selectAll`/`selectedCount` keys removed as dead; `backToDetails` added.
- Add/remove flow, avatar/name/followers row display, and the 3-dot delete context menu are otherwise byte-for-byte unchanged.
- This closes Sprint 8's E13 epic (nav restructure). E16-S1 (Анализ teaser) and E15-S1/S2/S3 (run detail: AI summary, top-5-by-virality, Summary+Publications tabs) remain backlog, not started this session — the user scoped this run to "E13 all stories" specifically.

## [E14-S1] Scheduled runs: schema and migration
**Epic:** Scheduled Runs
**Sprint:** 9 (locked 2026-07-22 execution plan)
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E3-S7 (reuses the duration_days/item_limit XOR pattern)
### Goal
A durable definition of a recurring run: which competitors, what scope (day window or last-N, per E3-S7), and which day-of-week + time to fire.
### Acceptance Criteria
- [x] New `scheduled_runs` table: project_id, account_ids scope (nullable = whole list, mirrors `AnalysisRun.account_ids`), duration_days/item_limit (same XOR CHECK pattern as `AnalysisRun`), day_of_week, time_of_day, timezone, active, created_by, last_run_id, migration via Alembic
- [x] Model exposed through `src/models/__init__.py` per existing convention
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test passed (deferred, see below)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Migration applies cleanly on DEV; `\d scheduled_runs` shows the expected columns and constraint.
### Files to read
CLAUDE.md, CONVENTIONS.md, backend/src/models/analysis_run.py (XOR constraint pattern to mirror)
### Files to create or modify
backend/src/models/scheduled_run.py (new), backend/alembic/versions/<new>.py, backend/src/models/__init__.py
### Handover
- `backend/src/models/scheduled_run.py:ScheduledRun` — mirrors `AnalysisRun`'s XOR `duration_days`/`item_limit` CHECK constraint (`duration_or_item_limit_range`) plus a new `day_of_week_range` CHECK (0=Monday..6=Sunday, matching `datetime.weekday()`). `timezone` is a plain IANA-name `String(64)` (no new dependency — Python 3.12 stdlib `zoneinfo` will resolve it in E14-S2's cron tick), Python-side default `"Europe/Moscow"`. `last_run_id` FK to `analysis_runs.id`, nullable, updated by E14-S2's dispatcher.
- Migration `f6a7b8c9d0e1` (now head, follows `a9b8c7d6e5f4`).
- `make_scheduled_run()` test helper added to `backend/tests/conftest.py`, same shape as `make_run()`.
- 4 new tests in `backend/tests/test_models.py`: roundtrip + defaults, XOR-rejected, both-set-rejected, day_of_week-out-of-range-rejected.
- **For E14-S2:** table is ready; the CRUD API + arq cron tick can be built directly on top.

## [E14-S2] Scheduled runs: CRUD API + arq cron dispatcher
**Epic:** Scheduled Runs
**Sprint:** 9
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E14-S1
### Goal
Users can create/list/update/delete scheduled runs via API, and a new recurring background job fires due schedules automatically — the first use of arq's cron scheduling in this codebase (today `WorkerSettings.functions` only lists on-demand jobs).
### Acceptance Criteria
- [x] `POST/GET/PATCH/DELETE /projects/{id}/scheduled-runs`, workspace-owned via the existing `get_owned_project` pattern
- [x] `WorkerSettings.cron_jobs` gains a tick function (e.g. every 5 minutes) that finds schedules due in the current window (day_of_week + time_of_day, respecting each schedule's timezone) and creates+enqueues an `AnalysisRun` the same way `POST /projects/{id}/runs` does today (reuses `estimate_run`/`enqueue_run`, respects the token-balance gate in `worker.py`)
- [x] A schedule that fires while its `token_balance` is exhausted behaves the same as a manual run hitting the same limit (partial/skip, never crashes the cron tick)
- [x] `last_run_id` updated after each fire, for display on the Scheduled Runs list (E14-S3)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [ ] CI green, deployed to DEV (pending push)
- [ ] Smoke test passed (deferred, see below)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Create a schedule for a near-future day/time on DEV, wait for it to fire, confirm a new run appears in Детали's run history without any manual trigger.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/services/queue.py, backend/src/api/runs.py (run-creation logic being reused), arq cron docs
### Files to create or modify
backend/src/api/scheduled_runs.py (new), backend/src/worker.py (`WorkerSettings.cron_jobs`), backend/src/services/scheduled_runs.py (new), backend/tests/test_scheduled_runs.py (new)
### Handover
- `backend/src/services/scheduled_runs.py` — `most_recent_occurrence_utc(schedule, before)` is a pure function (no DB) that finds the most recent UTC instant a schedule's `(day_of_week, time_of_day)` occurred in its own IANA timezone (stdlib `zoneinfo`, no new dependency); `is_due(schedule, now_utc, window_minutes)` wraps it. This "look back for the most recent occurrence" design was chosen over "does today's weekday match now's weekday" specifically to avoid a midnight-boundary gap (a schedule at 23:58 would never fire under the naive approach, since by the next 5-minute tick the weekday has already rolled over).
- `fire_due_schedules(session, now=None)` is the cron tick's core (testable without arq/Redis): loads active schedules, calls `_fire_one` for due ones. `_fire_one` mirrors `POST /projects/{id}/runs`' gates (`resolve_target_accounts` empty, `token_balance <= 0`, `max_runs_per_user_per_day` quota) but skips silently instead of raising an HTTPException — a cron tick has no user to show an error to. One schedule's exception is caught and rolled back without stopping the rest (`fire_due_schedules`'s try/except).
- `WorkerSettings.cron_jobs = [cron(check_scheduled_runs, minute=set(range(0, 60, 5)), second=0)]` (`backend/src/worker.py`) — ticks are aligned to `:00/:05/:10.../:55`, and `TICK_WINDOW_MINUTES = 5` exactly matches that cadence so consecutive windows tile the timeline with no gaps or double-fires.
- `backend/src/api/scheduled_runs.py` — `ScheduledRunIn` (full-replace body, used by both POST and PATCH, mirroring `ProjectUpdateIn`'s pattern rather than partial-PATCH semantics) validates the XOR scope (same as `RunRequestIn`) and the timezone string via `zoneinfo.ZoneInfo(...)`. Router mounted at `/projects/{project_id}/scheduled-runs` (prefix style, like `accounts.py`), registered in `main.py`.
- `test_models.py:test_schema_has_exactly_expected_tables` updated to include `scheduled_runs` — would have failed CI otherwise (same class of gap the E5-S5/E2-S3 post-close fixes hit).
- 22 new tests in `test_scheduled_runs.py`: 6 pure scheduling-math tests (ran locally, no DB needed — same-day/looks-back-a-week/timezone-respecting occurrence math, within/outside-window, wrong-day), 16 DB-integration tests (CRUD + 6 `fire_due_schedules` cases: fires, skips-not-due, skips-inactive, skips-exhausted-balance, skips-no-accounts, scope-preserved-on-created-run). `ruff format`/`ruff check`/`mypy src` clean.
- **For E14-S3:** the API is ready — `POST/GET/PATCH/DELETE /projects/{id}/scheduled-runs` returns `ScheduledRunOut` (includes `last_run_id` for the list's "last run" display).
- **Not added:** a "customize the cron tick interval" setting — hardcoded to 5 minutes like the AC's example, no ENV var, since nothing in this story needed it tunable.

## [E14-S3] Scheduled Runs page (list + create/edit)
**Epic:** Scheduled Runs
**Sprint:** 9
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E14-S2, E13-S2
### Goal
The frontend surface for E14-S2, reached via the "Запланированные запуски" button on Детали.
### Acceptance Criteria
- [x] List page: existing schedules (competitors scope, day/count scope, day-of-week + time, active toggle, last-run date), back button to Детали
- [x] Create/edit form: competitor multiselect, day-window/count-scope toggle (reuses the picker built in E3-S7's `run-dialog.tsx`), day-of-week + time picker, save
- [x] Usable at 375px (D16)
### Definition of Done
- [x] All AC checked
- [ ] Tests written and passing (no frontend unit test suite in this repo — CI gate is typecheck + eslint, per CONVENTIONS.md; both clean)
- [ ] CI green, deployed to DEV (pending push)
- [ ] Smoke test passed (deferred, see below)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
On DEV at 375px, create a schedule, see it listed, edit it, deactivate it — all persist correctly.
### Files to read
CLAUDE.md, DECISIONS.md (D16), frontend/app/(app)/projects/[id]/run-dialog.tsx (scope picker to reuse)
### Files to create or modify
frontend/app/(app)/projects/[id]/scheduled/page.tsx (new), frontend/app/(app)/projects/[id]/scheduled/scheduled-run-dialog.tsx (new), frontend/lib/api.ts, frontend/messages/ru.json
### Handover
- `frontend/lib/api.ts` — `ScheduledRunResponse`/`ScheduledRunRequest` types + `listScheduledRuns`/`createScheduledRun`/`updateScheduledRun`/`deleteScheduledRun`. `ScheduledRunRequest` is a full-replace body (used by both create and update), matching the backend's `ScheduledRunIn`.
- `frontend/app/(app)/projects/[id]/scheduled/page.tsx` — list of schedule cards (day/time, scope summary, competitor-count summary, last-run date, active checkbox toggling in place via PATCH), 3-dot context menu for delete (same pattern as `competitors/page.tsx`). The list's "last-run date" isn't on `ScheduledRunOut` directly (only `last_run_id`) — the page resolves it by fetching each referenced run via the existing `api.getRun`, deduped and in parallel, since this project's backend doesn't expose a joined "last run" summary and adding one wasn't worth a new endpoint for a handful of schedules per project.
- `frontend/app/(app)/projects/[id]/scheduled/scheduled-run-dialog.tsx` — reuses `run-dialog.tsx`'s day/count scope-mode toggle and picker verbatim (same option arrays, same visual pattern), adds a competitor multiselect (checkbox list from `api.listAccounts`, "Все конкуренты" checked by default = `account_ids: undefined`), a day-of-week button row (Пн..Вс), and a native `<input type="time">`. No timezone picker in the UI — always submits `"Europe/Moscow"` (or the existing schedule's stored value on edit), matching the model's default; the AC only asked for "day-of-week + time picker", and this is a Russian-only MVP for a single timezone market.
- `frontend/messages/ru.json` — new `ScheduledRuns` namespace (weekday labels, scope/account labels, dialog copy).
- Deviation from E13-S3: that story removed per-run competitor selection from manual run creation entirely (`Детали`'s "Создать запуск" always passes `accountIds: undefined` now). This story's multiselect is scoped to the *recurring schedule* definition only, per this story's own AC and mirroring `ScheduledRun.account_ids`'s design (E14-S1) — it does not reintroduce selection into the manual run flow.
- `tsc --noEmit` and `next lint` both clean. Verified visually via a temporary `frontend/app/dev-preview/scheduled/[id]` scratch route (mocked `window.fetch` for `/scheduled-runs`, `/accounts`, `/runs/:id`, since this page does live API calls) — list view, create dialog (scope toggle, multiselect reveal, weekday/time pickers), 3-dot delete menu, all screenshotted at desktop + 375px with no console errors, deleted before commit.
- **For E14-S4:** the create/edit dialog's scope+multiselect+day/time UI is self-contained in `scheduled-run-dialog.tsx` — E14-S4 wires a "Запланировать" branch into `run-dialog.tsx` itself rather than reusing this component directly (different entry point, per its own AC).

## [E14-S4] Wire Run-now / Schedule choice into Details' create-run flow
**Epic:** Scheduled Runs
**Sprint:** 9
**Status:** done
**Completed:** 2026-07-22
**Priority:** medium
**Depends on:** E14-S3, E13-S2
### Goal
Detали's single "Создать запуск" entry point offers both immediate and scheduled runs, instead of Scheduled Runs being a wholly separate flow.
### Acceptance Criteria
- [x] After picking competitors + scope, user chooses "Запустить сейчас" (existing `run-dialog.tsx` flow, unchanged) or "Запланировать" (branches into day-of-week + time picker, posts to the E14-S2 API instead of starting a run immediately)
### Definition of Done
- [x] All AC checked
- [ ] Tests written and passing (no frontend unit test suite in this repo — CI gate is typecheck + eslint, both clean)
- [ ] CI green, deployed to DEV (pending push)
- [ ] Smoke test passed (deferred, see below)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
From Детали, create a run both ways in one session — "now" starts immediately, "schedule" lands on the Scheduled Runs list instead.
### Files to read
CLAUDE.md, frontend/app/(app)/projects/[id]/run-dialog.tsx
### Files to create or modify
frontend/app/(app)/projects/[id]/run-dialog.tsx, frontend/messages/ru.json
### Handover
- `run-dialog.tsx` — new `launchMode: "now" | "schedule"` state (default `"now"`), a toggle placed after the scope picker (matching AC's "after picking competitors + scope"). `"now"` keeps the exact pre-existing `api.createRun` → `track()` → progress-polling flow untouched. `"schedule"` reveals a day-of-week button row + native `<input type="time">` (same visual pattern as `scheduled-run-dialog.tsx`, duplicated rather than shared since the two dialogs have different surrounding state/props and the picker itself is ~20 lines) and calls `api.createScheduledRun` with `account_ids: accountIds` (same prop the "now" path already used — still always `undefined`/whole-list per E13-S3, no new selection UI added here) and a hardcoded `timezone: "Europe/Moscow"`.
- A third render branch (`scheduled`, alongside the existing `!run` form and `run` progress views) shows a "Расписание создано" confirmation with a link to `/projects/[id]/scheduled` and a close button — schedules don't have a trackable in-progress state the way runs do, so there's nothing to poll.
- `frontend/messages/ru.json`'s `RunDialog` namespace gained `launchModeLabel/Now/Schedule`, `dayOfWeekLabel`, `timeOfDayLabel`, `weekday0..6`, `scheduleButton`, `scheduledTitle/Hint`, `goToScheduled`.
- `tsc --noEmit` and `next lint` both clean. Verified visually via a temporary `frontend/app/dev-preview/rundialog` scratch route (mocked `window.fetch` + wrapped in `RunTrackerProvider`, since `RunDialog` calls `useRunTracker()`): confirmed the "now" mode's form is pixel-identical to before, "schedule" mode reveals the day/time pickers and renames the confirm button, and submitting it shows the new confirmation screen — desktop + 375px, no console errors, deleted before commit.
- This closes the E14 epic (Sprint 9) except E14-S5 (Telegram notification for scheduled-run completion), which needs no frontend change.

## [E14-S5] Telegram notification for scheduled-run completion
**Epic:** Scheduled Runs
**Sprint:** 9
**Status:** done
**Completed:** 2026-07-22
**Priority:** low
**Depends on:** E14-S2
### Goal
A scheduled run's completion is announced to the user's linked Telegram account, same as manual runs today.
### Acceptance Criteria
- [x] Scheduled-run completions call the existing `notify_run_complete` path — same copy as manual runs for launch
- [x] Follow-up story (not this one) will customize the message once the desired "summary" content is specified by the user
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (1 new integration test; local run collects and passes offline steps — full DB run needs CI, per this project's standing pattern)
- [ ] CI green, deployed to DEV (pending push)
- [ ] Smoke test passed (deferred, see below)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
A scheduled run fires on DEV; the linked Telegram account receives the same completion DM a manual run would send.
### Files to read
CLAUDE.md, backend/src/services/telegram_notify.py
### Files to create or modify
backend/src/services/scheduled_runs.py (call site only — no changes to telegram_notify.py itself expected)
### Handover
- **No production code changed.** E14-S2's `_fire_one` already creates the `AnalysisRun` and calls the same `enqueue_run()` a manual `POST /projects/{id}/runs` uses — the arq job (`run_analysis` → `process_run`) that eventually calls `notify_run_complete(run, requesting_user)` has no idea whether the run it's processing came from a schedule or a manual click. There was no schedule-specific call site to add.
- Added `test_scheduled_run_completion_notifies_telegram` to `test_scheduled_runs.py` to prove this end-to-end rather than by inspection alone: fires a due schedule (`fire_due_schedules`), then runs the resulting `AnalysisRun` through the real `process_run` (same function `test_worker.py` exercises for manual runs), with `notify_run_complete` mocked — asserts it's called once with the schedule-originated run and the schedule's `created_by` user.
- `ruff format`/`ruff check`/`mypy src` clean; the new test collects correctly (`pytest --collect-only`) — full execution needs the CI Postgres service, consistent with every DB-touching test in this project (no local Postgres in this sandbox).
- **This closes the E14 epic (Sprint 9 — scheduled runs).**

## [E14-S6] Scheduled-run redesign: multi-day schedules, Once/Recurring, per-schedule notify toggle
**Epic:** Scheduled Runs
**Sprint:** unscheduled (direct user request, 2026-07-25, out of the locked Sprint 10 order)
**Status:** done
**Completed:** 2026-07-25
**Priority:** high
**Depends on:** E14-S1..S5
### Goal
Fix real-world breakage found on first use of scheduled runs (E14-S1..S5 shipped with every smoke test deferred — this is the first live feedback) and replace the one-row-per-weekday data model with one row per schedule holding an array of weekdays, an explicit Once/Recurring mode, and a per-schedule Telegram-notify toggle (default off).
### Acceptance Criteria
- [x] `ScheduledRun` stores `days_of_week: int[]` instead of a single `day_of_week` — one row represents the whole schedule regardless of how many days are selected
- [x] `mode`: `once` (exactly one day, next occurrence only, schedule auto-deactivates after firing) or `recurring` (1–7 days, fires every selected day indefinitely)
- [x] `notify_enabled: bool`, default `false` — gates whether *this schedule's* completions DM the user on Telegram; independent of manual-run notifications, which are unaffected
- [x] UI (`run-dialog.tsx`'s Schedule branch + `scheduled-run-dialog.tsx`) leads with the Once/Recurring choice, then the day picker (single-select under Once, multi-select under Recurring), then time, then the notify toggle; Recurring shows a persistent note that there is no end date — it runs until deactivated or tokens run out
- [x] A single API call creates/updates one schedule row, replacing the old "loop and POST once per selected day" client-side pattern
- [x] Root-caused why completion DMs never arrived in practice: the code path (`notify_run_complete`, called from `worker.py` for every run regardless of origin) was already correct by inspection; no test exercised it against a *real* Telegram token/worker deploy (every E14 smoke test was deferred). Likely cause is environment, not logic — see Handover.
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing (backend: schema/migration, service math over multi-day arrays, once-mode auto-deactivate, notify_enabled gating; ruff/mypy clean)
- [ ] CI green, deployed to DEV (pending push)
- [ ] Smoke test passed (deferred, see below — same standing pattern as every other E14 story)
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
DEFERRED (same pattern as E14-S1..S5): create a Recurring schedule with notify on for a near-future day/time on real DEV, confirm it fires within its 5-minute window, the run completes, and the linked Telegram account receives a DM with a link into the Mini App; separately confirm a `notify_enabled=false` schedule's completion sends no DM and an Once-mode schedule deactivates itself after firing.
### Files to read
CLAUDE.md, `backend/src/models/scheduled_run.py`, `backend/src/services/scheduled_runs.py`, `backend/src/api/scheduled_runs.py`, `backend/src/worker.py`, `backend/src/services/telegram_notify.py`, `frontend/app/(app)/projects/[id]/run-dialog.tsx`, `frontend/app/(app)/projects/[id]/scheduled/scheduled-run-dialog.tsx`, `frontend/app/(app)/projects/[id]/scheduled/page.tsx`
### Files to create or modify
New migration; `backend/src/models/scheduled_run.py`, `backend/src/models/analysis_run.py` (new `notify_on_complete` column), `backend/src/models/__init__.py`, `backend/src/services/scheduled_runs.py`, `backend/src/api/scheduled_runs.py`, `backend/src/worker.py`; `frontend/lib/api.ts`, `run-dialog.tsx`, `scheduled-run-dialog.tsx`, `scheduled/page.tsx`, `frontend/messages/ru.json`
### Handover
- **Root cause of "no notifications sent":** `notify_run_complete` (services/telegram_notify.py) and its 3 call sites in `worker.py` were already correct by inspection — gated only on `settings.telegram_bot_token` and `user.telegram_id`. No test had exercised it against a real Telegram token/worker deploy; every E14 smoke test was deferred (see DONE.md's E14-S1..S5 entries). The most likely real-world cause is environment (`TELEGRAM_BOT_TOKEN` set on `api` but possibly not on `worker` — Sprint 6's human prerequisites asked for both) or simply that no schedule had ever fired in production — this session could not check Railway env vars directly. Separately, this story changes the *default* behavior regardless: scheduled runs now only notify when their `notify_enabled` toggle is explicitly turned on (previously every scheduled run notified unconditionally, same as manual runs, which is likely a second reason completion DMs felt broken/inconsistent to the user).
- **Schema:** `ScheduledRun.day_of_week: int` → `days_of_week: int[]` (one row = one schedule, any number of days); new `mode` (`once`/`recurring`, `ScheduleMode` enum) and `notify_enabled: bool` (default `false`). New `AnalysisRun.notify_on_complete: bool` (default `true`, preserving existing manual-run behavior) — set to `schedule.notify_enabled` when a run is created by `_fire_one`. Migration `a1b2c3d4e5f6` (now head): backfills each existing single-day row to `days_of_week=[day_of_week]`/`mode=recurring` (behaviorally identical), verified with a real up/down/up round-trip against a local Postgres.
- **Postgres gotcha caught by a test:** the array CHECK constraint's first draft used `array_length(days_of_week, 1) >= 1` to reject an empty array — Postgres's `array_length` returns `NULL` (not `0`) for a zero-length array, and a `NULL` result in a CHECK constraint is treated as passing, not violated. `test_scheduled_run_empty_days_of_week_rejected` caught this immediately; fixed by switching to `cardinality(days_of_week) >= 1`, which does return `0` for an empty array.
- `services/scheduled_runs.py`: `most_recent_occurrence_utc`/`is_due` now check membership across all of a schedule's `days_of_week` rather than a single day. `_fire_one` sets the new run's `notify_on_complete` from `schedule.notify_enabled`, and deactivates (`active=False`) `once`-mode schedules right after they fire — `recurring` schedules are untouched and keep firing every selected weekday indefinitely.
- `api/scheduled_runs.py`: `ScheduledRunIn` validates `days_of_week` (1-7 entries, in range, no duplicates) and that `mode="once"` implies exactly one day.
- `worker.py`: all three `notify_run_complete` call sites (done/cancelled/failed) now additionally gate on `run.notify_on_complete`.
- Frontend: `run-dialog.tsx`'s Schedule branch and `scheduled-run-dialog.tsx` both replaced with: Once/Recurring segmented (first), weekday chips (single-select under Once, multi-select under Recurring — switching to Once truncates any existing multi-day selection to its first day), time picker, a persistent "no end date" hint under Recurring, and a Telegram-notify switch (default off). Both dialogs now make exactly one `createScheduledRun`/`updateScheduledRun` call instead of looping once per selected weekday. `scheduled/page.tsx`'s list cards and context-menu title now render the full `days_of_week` list plus a notify badge; `details/page.tsx`'s KPI subtitle does the same for its "next scheduled run" summary.
- `bottom-nav.tsx` (mobile — the Mini App's primary nav, per this project's mobile-first priority): the active tab was previously distinguished only by an icon/label color change (accent olive vs. secondary grey) which reads as barely-there at a glance; now the active tab gets a filled `bg-ink`/`text-lime` pill behind the icon plus a bold label, matching the pill treatment already used elsewhere in this design system (e.g. the day-of-week chips). The desktop tab bar (`tabChipClass` in `components/ui/index.tsx`) already had a strong `bg-ink text-white` active state and needed no change.
- **This sandbox unexpectedly has a working local Postgres** (`localhost:5432`, `scout`/`scout`) — contrary to this project's long-standing "no local Postgres in this sandbox" assumption recorded across every prior E14 story's smoke-test deferral. The `content_scout_test` database didn't exist yet and was created manually this session (`CREATE DATABASE content_scout_test`) so `migrated_db`'s `alembic downgrade base` fixture could run. With it, the full backend suite actually ran end-to-end for the first time in this project's history: 238 tests pass, migration round-trips clean (`upgrade head` → `downgrade -1` → `upgrade head`), `ruff format`/`ruff check`/`mypy src` all clean. Worth re-checking in a future session whether this Postgres persists — if so, the "DEFERRED" smoke-test pattern used throughout DONE.md may no longer be the right default for future stories in this environment.
- Frontend verified via a temporary `frontend/app/dev-preview/scheduling` scratch route (mocked `window.fetch`, direct import of both real dialog components) — Once ⇄ Recurring toggle, multi-day selection collapsing to one day on switching to Once, the notify switch, and the bottom-nav pill highlight all confirmed visually in the Browser pane at desktop width; deleted before this commit, `tsc --noEmit`/`next lint` clean.
- Real end-to-end verification (a schedule actually firing on DEV and a Telegram DM arriving) remains deferred — same standing pattern as every other E14 story; this needs a live Railway DEV environment with `TELEGRAM_BOT_TOKEN` confirmed set on **both** `api` and `worker`.

## [E15-S1] Run-level AI summary generation
**Epic:** Run Detail View
**Sprint:** 8 (locked 2026-07-22 execution plan)
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E4-S2 (per-item summaries already exist), E3-S7
### Goal
Once a run finishes scraping + summarizing every item, one additional Claude call synthesizes an overview: what competitors are posting about, which topics trend toward higher virality, and a top-5 topic list.
### Acceptance Criteria
- [x] New prompt documented in `docs/PROMPTS.md`, fed all item captions/per-item summaries for the run
- [x] Output: 2–4 sentence overall summary (RU) + top-5-topics list; stored on a new `run_summaries` table (or JSON column on `AnalysisRun` — pick whichever avoids a join for the common read path) keyed by run_id
- [x] Triggered once, at the end of `process_run`, never re-run on every page view
- [x] New `usage_events` row for this Claude call (D12 — every external cost recorded at the moment it's incurred, no retrofits)
- [x] Failure of this step is non-fatal to the run (mirrors `notify_run_complete`'s never-raises pattern) — a run can be "done" with items but a pending/failed summary, surfaced gracefully in E15-S3
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — DEFERRED, see below
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
A finished DEV run gets a plausible Russian summary and top-5 topics within the pipeline's normal completion time; `usage_events` gained exactly one row for it.
### Files to read
CLAUDE.md, docs/PROMPTS.md, backend/src/services/summarize.py (E4 prompt patterns to follow), backend/src/worker.py (`process_run`)
### Files to create or modify
backend/src/services/run_summary.py (new), backend/src/models/run_summary.py or migration adding a column to analysis_run.py, backend/src/worker.py, docs/PROMPTS.md, backend/tests/test_run_summary.py (new)
### Handover
- **Note:** "files to read" listed `backend/src/services/summarize.py` — the actual filename (confirmed via `ls`) is `summarizer.py`; read the correct file.
- Chose the JSON-column-on-`AnalysisRun` option over a separate `run_summaries` table, per the AC's own "pick whichever avoids a join for the common read path" guidance — E15-S3's run detail page already loads the `AnalysisRun` row, so no join needed.
- `RunSummaryStatus` enum (`pending`/`done`/`failed`) + `AnalysisRun.summary_status`/`summary_text`/`summary_topics` (`ARRAY(String(100))`)/`summary_generated_at` — migration `a9b8c7d6e5f4` (now head, on top of `b8c4d5e6f7a1`).
- `backend/src/services/run_summary.py:generate_run_summary(session, run, *, user_id, client=None)` — queries the run's `ContentItem`s joined to `Account` for handles (newest-published-first, capped at 150 items via `_MAX_ITEMS` to bound token cost), feeds each item's `summary` (falls back to raw `caption` if summarization itself failed/was skipped) to one Claude call using `settings.summary_model`, parses the `РЕЗЮМЕ:`/`ТЕМЫ:` text-protocol response via a pure, independently-unit-tested `parse_summary_response()` function. Records one `KIND_CLAUDE_INPUT_TOKENS` + one `KIND_CLAUDE_OUTPUT_TOKENS` usage_events row (matching every other Claude-call site in this codebase, which always records the pair — the AC's "a usage_events row" reads as "record this call's cost", not literally one row). Never raises: no items, an API exception, or an unparseable response all set `summary_status=failed` and return normally (unparseable specifically still stores the raw text as `summary_text` with empty `summary_topics`, since a raw response is still better than nothing).
- `backend/src/worker.py:process_run` — call added right before `rollup_run_totals`/`run.status=done`, reusing the same `anthropic_client`/`http_client` already open for per-item summarization; wrapped in an extra try/except at the call site (belt-and-suspenders, matching the defensive style already used around `notify_run_complete`) even though the service itself never raises.
- `docs/PROMPTS.md` — new "Run summary (E15-S1)" section, system+user prompt verbatim-mirrored in the service per this repo's convention.
- **For E15-S3 (next):** these fields aren't exposed via any API endpoint yet — this story's AC only required "stored", and no `api/runs.py` change was in its file list. E15-S3's run-detail page will need to either add these fields to `RunOut`/`GET /runs/{id}` or introduce a dedicated run-detail endpoint.
- No new dependencies, no ENV vars. 11 new tests in `test_run_summary.py` (3 pure `parse_summary_response` unit tests, 5 DB-backed `generate_run_summary` integration tests covering happy path, caption-fallback, no-items, API-error-non-fatal, and unparseable-response-still-stores-text). `ruff format`/`ruff check`/`mypy src` all clean locally via the project's `.venv`; `alembic heads` confirms a single linear head (`a9b8c7d6e5f4`) with no branching. pytest itself needs the CI Postgres service (no local Postgres in this sandbox, consistent with every prior story).
**Smoke test:** DEFERRED — needs a real finished DEV run to confirm a plausible Russian summary + top-5 topics land within normal completion time and exactly one input+output usage_events pair is recorded (same deferral pattern as the rest of this project's Apify/Claude-dependent verification).

## [E15-S2] Top-5-posts-by-virality for a run
**Epic:** Run Detail View
**Sprint:** 8
**Status:** done
**Completed:** 2026-07-22
**Priority:** medium
**Depends on:** E5-S5 (virality), E12-S3 (SQL `virality_ratio_expr`)
### Goal
Surface the 5 most viral posts of a run — no new modeling needed, this is purely `virality_ratio_expr` sorted desc with a limit, exposed for the run-summary view.
### Acceptance Criteria
- [x] Existing items endpoint (or the new run-summary endpoint from E15-S1) supports returning the top 5 by virality ratio for a given run, reusing `virality_ratio_expr` from `services/metrics.py`
- [x] Items with insufficient sample size (per `virality_min_items`) are excluded, same as the existing badge logic
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — DEFERRED, see below
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
For a finished DEV run with ≥5 qualifying items, the returned top-5 matches manually sorting the Publications tab by virality descending.
### Files to read
CLAUDE.md, backend/src/services/metrics.py
### Files to create or modify
backend/src/api/items.py or the new run-summary endpoint from E15-S1, backend/tests/test_items_api.py
### Handover
- New `GET /runs/{run_id}/top-virality?limit=5` (`backend/src/api/items.py:list_top_virality_items`, `TopViralityOut`) — a dedicated endpoint rather than extending E15-S1's run-summary storage (E15-S1 stores fields on `AnalysisRun`, not an endpoint), and rather than overloading the existing paginated `/runs/{run_id}/items` (different response shape, no pagination needed for a fixed top-N). Reuses `ContentItemOut` for the item shape so the frontend gets a type it already knows, and can reuse it to link into the Publications tab (per E15-S3's AC).
- Query mirrors `list_run_items`'s existing virality join (`virality_baseline_subquery` + `virality_ratio_expr`), filtered with `.where(virality_expr.isnot(None))` (excludes insufficient-sample items entirely, rather than just sorting them last as the general sort does) and `.order_by(virality_expr.desc()).limit(limit)`. `limit` is query-param-configurable (1–20, default 5) in case E15-S3 wants a different count later.
- Row-to-`ContentItemOut` mapping is duplicated from `list_run_items`/`list_project_items` rather than extracted into a shared helper — matches this file's existing style (the two pre-existing endpoints already duplicate this same block); no refactor of the untouched endpoints, out of scope for this story.
- 3 new tests in `test_items_api.py`: excludes-insufficient-sample + orders desc, respects the `limit` query param (default 5, explicit 2), scoped to owning workspace (404 for a foreign user) — reusing the same fixture pattern as the existing `test_sort_by_virality`. `ruff format`/`ruff check`/`mypy src` clean; endpoint import-sanity-checked. No new dependencies, no ENV vars, no migration.
**Smoke test:** DEFERRED — needs a real finished DEV run with ≥5 qualifying items to confirm the returned top-5 matches manually sorting the Publications tab by virality descending.

## [E15-S3] Run detail page: Summary + Publications tabs
**Epic:** Run Detail View
**Sprint:** 8
**Status:** done
**Completed:** 2026-07-22
**Priority:** high
**Depends on:** E15-S1, E15-S2, E13-S2, E12-S3
### Goal
Opening a run card from Детали lands on a dedicated run-detail page with two tabs, replacing the ad-hoc "click a history row to filter Результаты by run_id" pattern.
### Acceptance Criteria
- [x] New route `/projects/[id]/runs/[runId]` with Summary/Publications tabs
- [x] Summary tab: run date/time, accounts analyzed, publications analyzed, AI overall summary + top-5 topics (E15-S1), top-5 posts by virality (E15-S2, linking into the Publications tab)
- [x] Publications tab: reuses `results-cards`/`results-controls` scoped to this run, with the **run-filter icon removed** (redundant — already scoped to one run); sort/star/export controls unchanged
- [x] The existing project-wide Результаты tab (bottom nav) is untouched — this is a new, additional scoped view, not a replacement
- [x] Telegram run-completion notifications (`notify_run_complete`) link here instead of `/results?run=...`
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — DEFERRED, see below
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
From Детали, open a finished run — Summary tab shows plausible data, Publications tab behaves like Результаты minus the run-filter icon, and a Telegram completion DM's link lands here.
### Files to read
CLAUDE.md, DECISIONS.md (D16, D28), frontend/components/results-cards.tsx, frontend/components/results-controls.tsx, frontend/app/(app)/projects/[id]/results/page.tsx
### Files to create or modify
frontend/app/(app)/projects/[id]/runs/[runId]/page.tsx (new), frontend/lib/api.ts, backend/src/services/telegram_notify.py (link target), frontend/messages/ru.json
### Handover
- **Backend deviation (anticipated in E15-S1/E15-S2's own handovers):** neither prior story exposed its data via the API, so this story additionally touched `backend/src/api/runs.py` — extended `RunOut`/`GET /runs/{id}` with `summary_status`/`summary_text`/`summary_topics` (straight passthrough from the `AnalysisRun` columns E15-S1 added). E15-S2's `GET /runs/{run_id}/top-virality` needed no change — already a standalone endpoint, called directly from the new page.
- `frontend/app/(app)/projects/[id]/runs/[runId]/page.tsx` (new) — tab state is local (`useState<"summary"|"publications">`), no URL query param (this is a fresh route, not a modification of `/results`, so there was no existing deep-link contract to preserve). Summary tab gates all content on `run.status === "done"` (matches `results/page.tsx`'s existing `showItems` gating pattern) and additionally branches on `run.summary_status` for the AI-overview block (`done` → text + topic chips, `failed` → RU fallback message, `pending` → RU "unavailable" message — the last covers pre-E15-S1 runs whose `summary_status` defaults to `pending` forever, not an in-flight state a client will realistically observe since `generate_run_summary` resolves synchronously before `run.status` flips to `done`). Top-5-by-virality cards are clickable — each sets `tab = "publications"` (the AC's "linking into the Publications tab"; no deep-scroll-to-item, not requested).
- **Publications tab reuses `listProjectItems` (`GET /projects/{id}/items?run_id=...`), not `listRunItems`** — deliberate choice over the seemingly more obvious `GET /runs/{run_id}/items`: only the project-items endpoint supports `starred_only`, which the AC's "star... controls unchanged" requires. This gives full sort/star/export parity with zero additional backend work, with `run_id` simply pinned instead of user-selectable.
- **Run-filter icon removal** needed no change to `results-controls.tsx` — passing `runs={[]}` to `ResultsControlsBar` already suppresses the icon (`{runs.length > 0 && (...)}` in the existing component), so the shared component is untouched.
- Desktop Publications tab has no export button, matching `results/page.tsx`'s existing behavior exactly (export is mobile-only there too, pre-existing gap in this codebase, not something introduced or fixed by this story).
- Telegram link (`telegram_notify.py`) now points at `/projects/{project_id}/runs/{run.id}` instead of `/results?run=...`.
- 2 new backend tests in `test_runs.py` (`GET /runs/{id}` surfaces summary fields; defaults to `pending`/`None` for pre-migration runs), 1 existing test in `test_telegram_notify.py` tightened to assert the new link path exactly. `ruff format`/`ruff check`/`mypy src` clean. Frontend: no unit test suite exists in this repo (CI gate is typecheck + eslint); both clean. Verified visually via a temporary `frontend/app/dev-preview/projects/[id]/runs/[runId]` scratch route with a mocked `window.fetch` (the page makes live API calls rather than taking props, so — unlike prior scratch previews that just mounted a presentational component — this one intercepted `fetch` by URL pattern to exercise the real page end-to-end), covering: done run with `summary_status=done`/`failed`, non-done run status gating, top-5-card → Publications-tab navigation, and the run-filter icon's absence. Screenshotted at desktop + 375px, no console errors, deleted before commit.
- **This closes Sprint 8.** All three epics (E13 nav restructure, E16 Analysis teaser, E15 run detail) are now done — see SPRINT.md for the Sprint 9 (E14 scheduled runs) handoff.
- **POST-CLOSE CORRECTION (2026-07-22, same-day):** per direct user feedback, this page is no longer reached from Детали. Результаты is now the run-history landing page (the "Создать запуск" button + run-history cards moved here from E13-S2's Детали page), and clicking a run card lands here directly. The back link at the top of this page now reads "← Результаты" and routes to `/projects/[id]/results` (was "← Детали" → `/projects/[id]/details`). The global run-notification dropdown (`frontend/app/(app)/layout.tsx`) and `telegram_notify.py`'s completion-DM link both already pointed here and needed no further change.
**Smoke test:** DEFERRED — needs a real DEV project with a finished run to confirm the Summary tab's live data, the Publications tab's parity with Результаты minus the run-filter icon, and that a real Telegram completion DM's link lands here (same deferral pattern as the rest of this project's verification).

## [E16-S1] Analysis teaser page
**Epic:** Analysis Teaser
**Sprint:** 8 (locked 2026-07-22 execution plan)
**Status:** done
**Completed:** 2026-07-22
**Priority:** low
**Depends on:** E13-S1
### Goal
The third bottom-nav tab, Анализ, is a placeholder for future paid deep-analysis products — not functional yet, just a preview of what's coming.
### Acceptance Criteria
- [x] Route `/projects/[id]/analysis` reuses the existing "coming soon" visual pattern from the now-removed `/create` page (Sparkles icon + centered text)
- [x] Lists disabled cards for: competitor deep-dive, run deep-dive, publication deep-dive + rewritten-script generation — short RU description each, no functionality
- [x] Old `/create` route deleted (superseded — see E13-S1)
### Definition of Done
- [x] All AC checked
- [x] Tests written and passing
- [x] CI green, deployed to DEV
- [ ] Smoke test passed — DEFERRED, see below
- [x] DONE.md updated
- [x] BACKLOG.md updated
### Smoke test
Tapping Анализ on DEV shows the teaser cards, nothing clickable does anything, no console errors.
### Files to read
CLAUDE.md, frontend/app/(app)/projects/[id]/create/page.tsx (pattern being repurposed)
### Files to create or modify
frontend/app/(app)/projects/[id]/analysis/page.tsx (new, repurposes create/page.tsx), frontend/app/(app)/projects/[id]/create/page.tsx (delete), frontend/messages/ru.json
### Handover
- **Note:** by the time this story started, E13-S1 had already deleted `/create` and created the `/analysis` stub (Sparkles "coming soon"). The "files to read/modify" list above (written when the story was drafted) referenced the not-yet-deleted `/create` page as the pattern source — that file no longer existed, so the current `/analysis` stub was read directly instead. No functional difference: same visual pattern, just already relocated.
- `frontend/app/(app)/projects/[id]/analysis/page.tsx` — kept the existing Sparkles/title/comingSoon block, added a 3-card grid below (`grid-cols-1 sm:grid-cols-3`) using the shared `Card`/`Badge` components: Разбор конкурента (Users icon), Разбор запуска (TrendingUp icon), Разбор публикации (FileText icon, covers "publication deep-dive + script generation" as one card per the existing `comingSoon` copy, which already describes it as one combined item). Each card is `opacity-60`, `cursor-not-allowed`, `aria-disabled`, with a "Скоро" badge — no click handlers, no functionality.
- `frontend/messages/ru.json` — new `Analysis.cards.{badge,competitor,run,publication}` keys (title+description per card).
- No backend changes, no new dependencies, no ENV vars.
- No frontend unit test suite exists in this repo (CI gate is typecheck + eslint per CONVENTIONS.md); both clean (`tsc --noEmit`, `next lint`). Verified visually via a temporary `frontend/app/dev-preview/analysis` scratch route (imported the real page component directly, no mock props needed since it takes none), screenshotted at desktop (1600px) and 375px, deleted before commit.
**Smoke test:** DEFERRED — needs a real DEV project open on the Анализ tab to confirm the live cards render with no console errors (same deferral pattern as the rest of this project's verification).

## [E17-S1] Deep analysis schema, pricing config, and token-charge plumbing
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11, after E8-S3 — 2026-07-25 brainstorm session)
**Status:** backlog
**Priority:** medium
**Depends on:** E16-S1
### Goal
The data model, config, and token-deduction plumbing a deep analysis needs to exist and be paid for, before any scraping or Claude work happens.
### Acceptance Criteria
- [ ] `deep_analyses` table: id, run_id, project_id, requested_by, status (`pending`/`extracting`/`synthesizing`/`done`/`failed`), tokens_charged, report_stats (JSONB), report_recommendations (JSONB), error_message, created_at, completed_at — Alembic migration
- [ ] Config: `deep_analysis_token_multiplier` (placeholder value, explicitly flagged non-final per D35) and `deep_analysis_comments_per_post` (default 25, per D34)
- [ ] The start endpoint (wired in E17-S5) checks `user.token_balance >= items_count * deep_analysis_token_multiplier` before enqueueing and deducts up front, reusing the `insufficient_token_balance` guard pattern already in `api/runs.py`
- [ ] A deep analysis can only be started against a run with `status=done`
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV, attempt to start a deep analysis with insufficient balance — rejected with the same Russian error pattern as run creation; with sufficient balance, tokens deduct immediately and a `pending` row appears.
### Files to read
CLAUDE.md, DECISIONS.md (D26, D32–D35), backend/src/models/analysis_run.py, backend/src/api/runs.py, backend/src/models/user.py
### Files to create or modify
backend/src/models/deep_analysis.py (new) + migration, backend/src/config.py, backend/tests/test_deep_analysis_model.py
### Handover
—

## [E17-S2] Comment scraping: Bright Data primary, Apify fallback
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11)
**Status:** backlog
**Priority:** high
**Depends on:** E17-S1
### Goal
Fetch up to `deep_analysis_comments_per_post` comments per analyzed publication, trying Bright Data's Instagram Scraper API first and falling back automatically to Apify's official `instagram-comment-scraper` if Bright Data fails — the first application of the "external services get a documented fallback vendor" pattern (D32).
### Acceptance Criteria
- [ ] `fetch_comments(item, limit) -> list[RawComment]` lives in a new narrow service, not the `Platform` protocol — this is single-platform, dual-vendor, scoped only to deep analysis, per D32's note that this doesn't generalize to a new abstraction
- [ ] Bright Data client wrapped with timeout + retry (per CONVENTIONS.md); on exhausted retries or an error response, falls back to the Apify comment actor for that same post rather than failing the item
- [ ] Per-post failure (both vendors fail) doesn't fail the whole analysis — post is skipped, degrades gracefully (ties into E17-S9)
- [ ] Whichever vendor actually served each fetch is recorded distinctly in `usage_events` (`brightdata_comment_result` / `apify_comment_result` kinds, each with their own `unit_cost_usd`) so real per-vendor cost and fallback rate are visible in the ledger
- [ ] Verify empirically (spike, documented in Changelog) whether either vendor returns comments in engagement order; if not, sort client-side by `likes` before truncating to the cap
- [ ] Integration tests against recorded fixtures for both vendors (no live Bright Data/Apify calls in CI, per CONVENTIONS.md)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Run a deep analysis on DEV against a real project — comments are fetched for its posts; temporarily invalidating the Bright Data token confirms the Apify fallback path serves the same request successfully.
### Files to read
CLAUDE.md, DECISIONS.md (D2, D32, D34), backend/src/platforms/instagram.py (retry/timeout pattern to mirror), backend/src/models/usage_event.py, ENV.md
### Files to create or modify
backend/src/services/comment_scraper.py (new), backend/src/config.py, backend/tests/test_comment_scraper.py, backend/tests/fixtures/brightdata_comments_sample.json, backend/tests/fixtures/apify_comments_sample.json, ENV.md, DECISIONS.md
### Handover
—

## [E17-S3] Per-item extraction pass (Haiku)
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11)
**Status:** backlog
**Priority:** high
**Depends on:** E17-S2
### Goal
One Claude Haiku call per analyzed item that tags content signals (topic, format, hook type, CTA presence) and, from E17-S2's fetched comments, extracts sentiment plus the top complaints/praises/unanswered questions/notable phrases — structured JSON, not prose.
### Acceptance Criteria
- [ ] Prompt documented in `docs/PROMPTS.md`; model is `claude-haiku-4-5` per D33
- [ ] Reuses `summarizer.py`'s batching/concurrency/retry scaffolding and D29's cost policy (512px images where a cover is used, Message Batches API for batches ≥20 items)
- [ ] Output stored per-item so E17-S4 can consume it without re-querying comments (new `deep_analysis_items` table, one row per content_item per deep_analysis)
- [ ] A failed/unparseable extraction for one item doesn't fail the analysis — degrades to metrics-only for that item, matching the fallback-tolerant pattern used throughout this pipeline
- [ ] `claude_input_tokens`/`claude_output_tokens` usage_events written per D12
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV, a deep analysis's extraction phase completes for all items in a finished run; usage_events gain the expected input/output token pairs.
### Files to read
CLAUDE.md, docs/PROMPTS.md, backend/src/services/summarizer.py, DECISIONS.md (D29, D33)
### Files to create or modify
backend/src/models/deep_analysis.py (add `deep_analysis_items` table + migration), backend/src/services/deep_analysis_extraction.py (new), docs/PROMPTS.md, backend/tests/test_deep_analysis_extraction.py
### Handover
—

## [E17-S4] Synthesis pass — full report (Sonnet)
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11)
**Status:** backlog
**Priority:** high
**Depends on:** E17-S3
### Goal
One Claude Sonnet call per deep analysis, fed the run's metrics (`services/metrics.py`) plus every item's E17-S3 extract, producing the full two-tab report as typed JSON: Статистика (topic frequency vs. virality, format/hook/CTA breakdown, cadence, comment-sentiment summary) and Рекомендации (ranked content ideas, do-more/do-less, hook templates, FAQ pack, posting-schedule suggestion, steal-this shortlist).
### Acceptance Criteria
- [ ] Prompt documented in `docs/PROMPTS.md`; model is `claude-sonnet-5` per D33 — the only non-Haiku call in this pipeline, matching D7's "stronger model reserved for the synthesis-type call" precedent
- [ ] Structured JSON output (tool-use/structured-output, not free text) matching a schema the frontend can render directly — mirrors E15-S1's parse-and-store pattern but richer
- [ ] Result stored on `deep_analyses.report_stats`/`report_recommendations`; `status` moves `extracting` → `synthesizing` → `done`/`failed`
- [ ] A failed or unparseable synthesis call sets `status=failed` with a Russian error message, never leaves the row stuck
- [ ] `claude_input_tokens`/`claude_output_tokens` usage_events written per D12
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
A DEV deep analysis reaches `done` with a plausible Russian report in both sections; a forced malformed-response case lands in `failed`, not stuck in `synthesizing`.
### Files to read
CLAUDE.md, docs/PROMPTS.md, backend/src/services/run_summary.py (closest existing single-call-synthesis pattern), DECISIONS.md (D33)
### Files to create or modify
backend/src/services/deep_analysis_synthesis.py (new), backend/src/worker.py (new arq job, thin-wrapper/core split per E2-S3's established pattern), docs/PROMPTS.md, backend/tests/test_deep_analysis_synthesis.py
### Handover
—

## [E17-S5] Deep Analysis API
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11)
**Status:** backlog
**Priority:** high
**Depends on:** E17-S4
### Goal
Endpoints to start a deep analysis, list a project's history, and poll/read one report — the same workspace-scoped ownership pattern as every other project-scoped router.
### Acceptance Criteria
- [ ] `POST /projects/{id}/runs/{runId}/deep-analyses` — validates run is `done`, checks/deducts token balance (E17-S1), enqueues the worker pipeline (E17-S2→S4)
- [ ] `GET /projects/{id}/deep-analyses` — history list, most recent first
- [ ] `GET /deep-analyses/{id}` — status while in progress, full report once `done`
- [ ] All routes 404 for foreign-workspace/missing ids via `get_owned_project`, matching every existing router
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV: start a deep analysis, poll it to `done`, list it in project history — all scoped correctly, a second user's project returns 404.
### Files to read
CLAUDE.md, backend/src/services/projects.py, backend/src/api/runs.py
### Files to create or modify
backend/src/api/deep_analyses.py (new), backend/src/services/queue.py, backend/tests/test_deep_analyses_api.py
### Handover
—

## [E17-S6] Analysis entry point: history + new-analysis picker
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11)
**Status:** backlog
**Priority:** medium
**Depends on:** E17-S5
### Goal
Wires E16-S1's disabled «Разбор запуска» card to a real page: a history list of past deep analyses plus a way to start a new one against a completed run.
### Acceptance Criteria
- [ ] «Разбор запуска» card in `/projects/[id]/analysis` becomes clickable, opens a history list (StatusPill, date, run reference, «Открыть» on done rows) with a lime «Новый анализ» pill
- [ ] New-analysis flow reuses the unified Sheet component (DESIGN_SYSTEM §4/§6): pick a completed run (date, item count), see the token cost (mono, lime-soft row, same visual pattern as the existing «Новый анализ» sheet's СТОИМОСТЬ section) before confirming
- [ ] Confirming starts the job and shows an in-progress state; the other two teaser cards (Разбор конкурента, Разбор публикации) remain disabled, untouched
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV/375px, tap «Разбор запуска», start a new analysis against a finished run, see it appear in-progress then move to done in the history list.
### Files to read
CLAUDE.md, DECISIONS.md (D31), docs/DESIGN_SYSTEM.md, frontend/app/(app)/projects/[id]/analysis/page.tsx, frontend/components/ui/bottom-sheet.tsx
### Files to create or modify
frontend/app/(app)/projects/[id]/analysis/page.tsx, frontend/components/deep-analysis-sheet.tsx (new), frontend/lib/api.ts, frontend/messages/ru.json
### Handover
—

## [E17-S7] Report page: Статистика tab
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11)
**Status:** backlog
**Priority:** medium
**Depends on:** E17-S6
### Goal
The Статистика half of the deep analysis report — what competitors post about, how often, and how well it performs.
### Acceptance Criteria
- [ ] New route `/projects/[id]/deep-analyses/[analysisId]`, Segmented control (Статистика/Рекомендации) per DESIGN_SYSTEM §4
- [ ] Topic frequency-vs-virality as a ranked card list with heat badges (not a scatter chart — stays consistent with the card-not-chart mobile mandate)
- [ ] Format/hook/CTA breakdown, posting cadence, comment-sentiment summary with representative quote cards
- [ ] Gracefully renders the degraded state from E17-S9 (comment-thin runs) without looking broken
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV/375px, open a done deep analysis — Статистика tab renders plausible topic/format/comment data with no console errors.
### Files to read
CLAUDE.md, docs/DESIGN_SYSTEM.md, frontend/components/results-cards.tsx (heat badge pattern to reuse)
### Files to create or modify
frontend/app/(app)/projects/[id]/deep-analyses/[analysisId]/page.tsx (new), frontend/lib/api.ts, frontend/messages/ru.json
### Handover
—

## [E17-S8] Report page: Рекомендации tab
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11)
**Status:** backlog
**Priority:** medium
**Depends on:** E17-S7
### Goal
The Рекомендации half of the report — the actionable output the add-on is actually sold on.
### Acceptance Criteria
- [ ] Ranked content-idea cards (topic, format, hook, one-line why) driven by `report_recommendations`
- [ ] Do-more/do-less list, hook templates, FAQ pack (unanswered questions from comments), posting-schedule suggestion
- [ ] Steal-this shortlist reuses `results-cards` visuals for the linked posts (deep-links into the run's Publications tab)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV/375px, the Рекомендации tab renders all sections with plausible content and working links into Publications.
### Files to read
CLAUDE.md, docs/DESIGN_SYSTEM.md, frontend/components/results-cards.tsx
### Files to create or modify
frontend/app/(app)/projects/[id]/deep-analyses/[analysisId]/page.tsx, frontend/messages/ru.json
### Handover
—

## [E17-S9] Thin-comment-data fallback and partial pricing
**Epic:** Run Deep Analysis
**Sprint:** unassigned (proposed Sprint 11, stretch — do after real DEV usage data shows how often this fires)
**Status:** backlog
**Priority:** low
**Depends on:** E17-S2, E17-S4
### Goal
When a run's comments come back sparse or empty (disabled/restricted comments, both vendors failing per-post), the report degrades to content-layer-only insights instead of a broken/empty comment section, and the customer isn't charged the full "with comments" price for a comments-empty result.
### Acceptance Criteria
- [ ] Below a configurable comment-coverage threshold, `report_stats`/`report_recommendations` omit comment-derived sections rather than rendering them empty
- [ ] Tokens charged reflect actual coverage (e.g. a reduced multiplier when comment coverage falls below the threshold) rather than the full rate always assumed at E17-S1's up-front deduction
- [ ] Frontend (E17-S7/S8) shows a clear Russian note when comment-derived sections were skipped, not a silent gap
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
A DEV deep analysis against a project with comments disabled on most posts completes with a graceful degraded report and a reduced token charge.
### Files to read
CLAUDE.md, DECISIONS.md (D34, D35), backend/src/services/comment_scraper.py, backend/src/api/deep_analyses.py
### Files to create or modify
backend/src/services/deep_analysis_synthesis.py, backend/src/api/deep_analyses.py, frontend/app/(app)/projects/[id]/deep-analyses/[analysisId]/page.tsx
### Handover
—
