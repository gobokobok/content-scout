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

Post-MVP (not scheduled, first stories drafted below for E8–E11): VK ID + SMS auth (behind Telegram Login in priority per D18), YouTube/TikTok/Threads platforms, native mobile app (not planned — see D17), team workspaces, mobile card layout for tables (MVP ships responsive with horizontal-scroll tables per D16), RU infra migration stages 2–3 (D20, infra-only, tracked outside BACKLOG.md until scheduled).

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
- [x] Push to `main` deploys backend + frontend to Railway DEV
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
**Status:** ready
**Priority:** high
**Depends on:** E1-S1
### Goal
Full MVP schema in SQLAlchemy models with Alembic migrations, matching docs/ARCHITECTURE.md.
### Acceptance Criteria
- [ ] Models: users, workspaces, workspace_members, projects, account_lists, accounts, analysis_runs, content_items, shortlist_items, usage_events (fields per docs/ARCHITECTURE.md)
- [ ] Alembic initialized; one migration creates the full schema; `alembic upgrade head` works on a fresh DB
- [ ] Constraints enforced in DB: ≤50 accounts per list (app-level check + partial safeguard), unique (account_list_id, normalized_url), run duration 1–7 days
- [ ] Model factory fixtures for tests
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Run `alembic upgrade head` against DEV database; tables exist (check via Railway psql).
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (data model section), backend/src/config.py
### Files to create or modify
backend/src/db.py, backend/src/models/*.py, backend/alembic/**, backend/tests/conftest.py, backend/tests/test_models.py
### Handover
—

## [E1-S3] Email+password auth and personal workspace
**Epic:** Foundation & Auth
**Sprint:** 1
**Status:** ready
**Priority:** high
**Depends on:** E1-S2
### Goal
Users can register and log in (JWT); registration auto-creates a personal workspace; frontend has Russian login/register pages and an authenticated shell.
### Acceptance Criteria
- [ ] `POST /auth/register` (email+password, bcrypt), `POST /auth/login` → JWT access token, `GET /auth/me`
- [ ] Registration creates a personal workspace and membership row in the same transaction
- [ ] Auth dependency rejects missing/invalid tokens with 401; all non-auth routes require it
- [ ] Frontend: /login and /register pages (Russian), token stored, authenticated layout with logout; unauthenticated users redirected to /login
- [ ] Auth provider kept behind an interface so VK ID can be added later without touching call sites
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Register a user on DEV, log out, log back in, see the authenticated shell in Russian.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (auth section), backend/src/models/user.py, frontend/messages/ru.json
### Files to create or modify
backend/src/auth/*.py, backend/src/api/auth.py, backend/tests/test_auth.py, frontend/app/(auth)/login/page.tsx, frontend/app/(auth)/register/page.tsx, frontend/lib/api.ts, frontend/messages/ru.json
### Handover
—

## [E2-S1] Project CRUD
**Epic:** Projects & Competitor Lists
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E1-S3
### Goal
A logged-in user can create, rename, list, and archive projects inside their workspace.
### Acceptance Criteria
- [ ] API: create/list/get/update/archive project, scoped to the caller's workspace (404 for foreign projects)
- [ ] Frontend: workspace home lists projects with "Создать проект"; project page shell with tabs (Конкуренты / Результаты / Шорт-лист / История)
- [ ] Archived projects hidden from default list
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Create a project on DEV, rename it, see it in the list; open it and see the four tabs.
### Files to read
CLAUDE.md, backend/src/models/project.py, backend/src/api/auth.py, frontend/lib/api.ts
### Files to create or modify
backend/src/api/projects.py, backend/tests/test_projects.py, frontend/app/(app)/projects/**, frontend/messages/ru.json
### Handover
—

## [E2-S2] Competitor list management (IG, max 50)
**Epic:** Projects & Competitor Lists
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E2-S1
### Goal
Within a project, the user manages the Instagram competitor list: paste/add URLs or @handles, validated and normalized, capped at 50, persisted.
### Acceptance Criteria
- [ ] API: add entries (single or bulk paste), remove entry, list entries — on the project's IG `account_list` (auto-created)
- [ ] URL/handle normalization to canonical `instagram.com/<handle>`; invalid entries rejected with per-line Russian error messages; duplicates deduped
- [ ] 51st entry rejected with a clear error; counter "N / 50" shown in UI
- [ ] Data model supports one list per platform (IG active; YouTube/TikTok/Threads platform enum values exist but are disabled in UI)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Paste 5 IG URLs (one invalid, one duplicate) on DEV — 3 saved, errors shown in Russian, counter reads 3 / 50.
### Files to read
CLAUDE.md, backend/src/models/account_list.py, backend/src/api/projects.py, frontend/app/(app)/projects/**
### Files to create or modify
backend/src/api/accounts.py, backend/src/services/url_normalizer.py, backend/tests/test_accounts.py, frontend/app/(app)/projects/[id]/competitors/**, frontend/messages/ru.json
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
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E2-S2
### Goal
User picks a duration (1–7 days), sees a cost estimate, confirms, and a run executes asynchronously through its full lifecycle using a mock scraper.
### Acceptance Criteria
- [ ] `POST /projects/{id}/runs/estimate` returns estimated Apify units + Claude tokens + ₽/$ cost for current list size × duration
- [ ] `POST /projects/{id}/runs` (after confirm) creates run `pending` and enqueues an arq job; duration outside 1–7 rejected
- [ ] Run optionally targets a **subset of accounts** (`account_ids` in the request; UI: checkboxes on the competitor list, default = entire list); estimate reflects the subset
- [ ] Worker advances run: pending → scraping → summarizing → done (mock platform returns fixture content); failures land in `failed` with error message
- [ ] `GET /runs/{id}` returns status + progress (accounts processed / total); frontend run dialog shows estimate → confirm → live progress
- [ ] `Platform` interface defined (`fetch_content(account, since) -> [RawContentItem]`); mock implementation registered
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV, start a run with the mock platform flag; watch status advance to done within a minute.
### Files to read
CLAUDE.md, docs/ARCHITECTURE.md (run lifecycle), backend/src/models/analysis_run.py, backend/src/api/projects.py
### Files to create or modify
backend/src/worker.py, backend/src/platforms/base.py, backend/src/platforms/mock.py, backend/src/services/estimator.py, backend/src/api/runs.py, backend/tests/test_runs.py, frontend/app/(app)/projects/[id]/run-dialog.tsx, frontend/messages/ru.json
### Handover
—

## [E3-S2] Apify Instagram integration and metrics
**Epic:** Analysis Pipeline
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E3-S1
### Goal
Real IG scraping: the worker fetches each account's content for the window via Apify, normalizes it into content_items, and computes derived metrics.
### Acceptance Criteria
- [ ] `InstagramPlatform` implements `Platform` using the Apify actor (actor id from env); raw payload stored in `content_items.raw` (JSONB)
- [ ] Normalized fields: published_at, type (reel/post/carousel), title (caption first line, truncated), url, likes, views (NULL for post/carousel), comments
- [ ] Derived: days_since_published, views_per_day, likes_per_day (computed at read time or run finish — per ARCHITECTURE.md)
- [ ] Apify units consumed recorded as `usage_events` per account fetch
- [ ] Per-account failures (private/deleted account) don't fail the run; account marked failed with reason, run completes partial
- [ ] Apify client wrapped with timeout + retry; integration test against recorded fixture (no live Apify in CI)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Run analysis on DEV against 2 real public IG accounts, 3 days — content_items rows appear with plausible metrics; usage_events rows exist.
### Files to read
CLAUDE.md, backend/src/platforms/base.py, backend/src/worker.py, backend/src/models/content_item.py, docs/ARCHITECTURE.md
### Files to create or modify
backend/src/platforms/instagram.py, backend/src/services/metrics.py, backend/tests/test_instagram_platform.py, backend/tests/fixtures/apify_ig_sample.json
### Handover
—

## [E4-S1] Claude summarization service
**Epic:** AI Summaries
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E3-S2
### Goal
A service that produces a 1–2 sentence Russian summary of a content item from its caption + cover image using Claude Haiku.
### Acceptance Criteria
- [ ] `summarize(items) -> summaries` batches requests to claude-haiku-4-5 with caption text + cover image (fetched from IG CDN URL, resized ≤1024px)
- [ ] Prompt in docs/PROMPTS.md; output: 1–2 sentences, Russian, describes what the content is about (no engagement commentary)
- [ ] Missing caption and unfetchable image handled (summarize from whichever exists; both missing → "Описание недоступно")
- [ ] Token usage per call recorded as usage_events
- [ ] Retries with backoff on rate limits; a failed summary never fails the run (item gets fallback text)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Trigger summarization for one real item on DEV; summary is Russian, 1–2 sentences, relevant to the post.
### Files to read
CLAUDE.md, docs/PROMPTS.md, backend/src/models/content_item.py, backend/src/services/usage.py (if exists)
### Files to create or modify
backend/src/services/summarizer.py, backend/tests/test_summarizer.py, docs/PROMPTS.md
### Handover
—

## [E4-S2] Summarization in the run pipeline
**Epic:** AI Summaries
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E4-S1
### Goal
The worker's `summarizing` phase runs the summarizer over all items of a run with bounded concurrency and progress reporting.
### Acceptance Criteria
- [ ] After scraping, run enters `summarizing`; items processed in batches with bounded concurrency (config)
- [ ] Progress (items summarized / total) exposed on `GET /runs/{id}` and shown in UI
- [ ] Run-level token totals rolled up onto analysis_runs (total_input_tokens, total_output_tokens, total_cost)
- [ ] Re-running summarization is idempotent (skips items that already have summaries)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Full run on DEV (2 accounts, 3 days): every item has a Russian summary; run shows token totals.
### Files to read
CLAUDE.md, backend/src/worker.py, backend/src/services/summarizer.py, backend/src/api/runs.py
### Files to create or modify
backend/src/worker.py, backend/src/services/usage.py, backend/tests/test_pipeline.py
### Handover
—

## [E5-S1] Results table
**Epic:** Results Table & Export
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E4-S2
### Goal
The Результаты tab shows the completed run's content as a table sortable by every column.
### Acceptance Criteria
- [ ] Columns: аккаунт, дата и время публикации, тип, заголовок, ссылка (opens IG in new tab), краткое описание, лайки, просмотры, дней с публикации, просмотров/день, лайков/день
- [ ] Server-side sort + pagination via `GET /runs/{id}/items?sort=&order=&page=`; every column sortable both directions
- [ ] Views columns show "—" (not 0) for post/carousel types; sort treats them as NULLs last
- [ ] Type shown as Russian labels with icons (Reels / Пост / Карусель)
- [ ] Run selector on the tab (defaults to latest completed run)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV open a finished run, sort by просмотров/день descending, click a link — IG post opens.
### Files to read
CLAUDE.md, backend/src/api/runs.py, docs/UI_GUIDELINES.md, frontend/app/(app)/projects/[id]/**
### Files to create or modify
backend/src/api/items.py, backend/tests/test_items_api.py, frontend/app/(app)/projects/[id]/results/**, frontend/components/results-table.tsx, frontend/messages/ru.json
### Handover
—

## [E5-S2] XLSX export
**Epic:** Results Table & Export
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
**Depends on:** E5-S1
### Goal
One click exports the current run's full results table to an .xlsx file with Russian headers.
### Acceptance Criteria
- [ ] `GET /runs/{id}/export.xlsx` streams a workbook (openpyxl): all rows, Russian headers matching the UI, link column as real hyperlinks, frozen header row, respects current sort
- [ ] Filename `content-scout_<project>_<run-date>.xlsx`
- [ ] "Экспорт в Excel" button on the results tab
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Export a DEV run, open in Excel/Numbers — headers Russian, links clickable, data matches UI.
### Files to read
CLAUDE.md, backend/src/api/items.py, frontend/app/(app)/projects/[id]/results/**
### Files to create or modify
backend/src/services/xlsx_export.py, backend/src/api/export.py, backend/tests/test_export.py, frontend/components/results-table.tsx
### Handover
—

## [E6-S1] Shortlist
**Epic:** Shortlist & History
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E5-S1
### Goal
User promotes rows from results to the project shortlist and manages them in the Шорт-лист tab.
### Acceptance Criteria
- [ ] Promote/demote action per results row (star toggle); API creates/removes shortlist_items (project-scoped, references content_item, survives across runs)
- [ ] **Bulk add:** row checkboxes + «выбрать все» with a «Добавить в шорт-лист» action for the selection (API accepts a list of item ids)
- [ ] Шорт-лист tab lists shortlisted items with same columns + добавлено (date shortlisted), sortable, removable
- [ ] Promoting the same item twice is idempotent (single or bulk)
- [ ] Placeholder "Создать сценарий" button visible but disabled with tooltip "Скоро" (script generation is post-MVP)
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
Promote 2 rows on DEV, open Шорт-лист — both there; remove one — gone; results row star reflects state.
### Files to read
CLAUDE.md, backend/src/models/shortlist_item.py, backend/src/api/items.py, frontend/components/results-table.tsx
### Files to create or modify
backend/src/api/shortlist.py, backend/tests/test_shortlist.py, frontend/app/(app)/projects/[id]/shortlist/**, frontend/messages/ru.json
### Handover
—

## [E6-S2] Run and shortlist history
**Epic:** Shortlist & History
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
**Depends on:** E6-S1
### Goal
The История tab shows all past runs (date, duration, accounts, items found, status, cost) and past shortlist activity; any past run's results can be reopened.
### Acceptance Criteria
- [ ] Run history list with: started_at, период (days), кол-во аккаунтов, найдено публикаций, статус, стоимость; click opens that run in the results tab
- [ ] Shortlist history: added/removed events with timestamps
- [ ] Failed runs show their error message in Russian
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
On DEV with ≥2 runs, open История, click the older run — its results render.
### Files to read
CLAUDE.md, backend/src/api/runs.py, frontend/app/(app)/projects/[id]/**
### Files to create or modify
backend/src/api/history.py, backend/tests/test_history.py, frontend/app/(app)/projects/[id]/history/**, frontend/messages/ru.json
### Handover
—

## [E7-S1] Usage rollups
**Epic:** Usage Metering & Admin
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E4-S2
### Goal
Usage events roll up into per-run and per-user totals, and the user sees their own consumption.
### Acceptance Criteria
- [ ] usage_events schema finalized: user_id, run_id, kind (apify_result | claude_input_tokens | claude_output_tokens), quantity, unit_cost_usd, created_at
- [ ] `GET /me/usage?from=&to=` returns totals per kind and cost, per project and overall
- [ ] Run history (E6-S2) cost column reads from these rollups
- [ ] Simple "Использование" page in account menu showing current month totals
### Definition of Done
- [ ] All AC checked
- [ ] Tests written and passing
- [ ] CI green, deployed to DEV
- [ ] Smoke test passed
- [ ] DONE.md updated
- [ ] BACKLOG.md updated
### Smoke test
After a DEV run, Использование page shows non-zero Apify results and Claude tokens for this month.
### Files to read
CLAUDE.md, backend/src/models/usage_event.py, backend/src/services/usage.py
### Files to create or modify
backend/src/api/usage.py, backend/tests/test_usage.py, frontend/app/(app)/usage/**, frontend/messages/ru.json
### Handover
—

## [E7-S2] Admin usage view
**Epic:** Usage Metering & Admin
**Sprint:** unassigned
**Status:** backlog
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
### Handover
—

## [E8-S1] Telegram Login
**Epic:** Telegram Integration & Monetization
**Sprint:** unassigned
**Status:** backlog
**Priority:** medium
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
**Sprint:** unassigned
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

## [E8-S3] Telegram Mini App + Stars subscriptions
**Epic:** Telegram Integration & Monetization
**Sprint:** unassigned
**Status:** backlog
**Priority:** high
**Depends on:** E8-S1, E7-S1
### Goal
The existing responsive frontend runs as a Telegram Mini App with `initData` auth, and users can subscribe to a usage plan paid in Telegram Stars.
### Acceptance Criteria
- [ ] Frontend loads inside Telegram via the Web App SDK; `initData` verified server-side and exchanged for the same JWT used elsewhere (extends `TelegramAuthProvider`, no login form shown inside Telegram)
- [ ] Subscription plans defined (included monthly usage-event allowance); `POST` flow creates a Telegram Stars invoice for a plan or a one-off top-up, confirmed via Bot API payment webhook
- [ ] Plan/usage balance visible on the existing «Использование» page (E7-S1); runs blocked with a clear Russian message when balance is exhausted, with a link to top up
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
