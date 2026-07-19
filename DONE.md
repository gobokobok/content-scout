# DONE — content-scout

Completed stories land here, newest first. Format:

## [E12-S2] Mobile cards, bottom navigation, UX states
**Completed:** 2026-07-19
**Handover:**
- `frontend/components/results-cards.tsx` — `ResultsCards` (card list + `SortBottomSheet` bottom sheet) and `ShortlistCards`; use `ResultsCards` i18n namespace
- `frontend/components/ui/skeleton.tsx` — `SkeletonLine`, `SkeletonCard`, `SkeletonList`, `SkeletonRow`, `SkeletonRows`
- `frontend/components/ui/toast.tsx` — `ToastProvider` (wrapped in root layout), `useToast()` → `addToast(msg, variant)`, 4s auto-dismiss
- `frontend/components/ui/bottom-nav.tsx` — `ProjectBottomNav` (md:hidden, env(safe-area-inset-bottom), ≥44px tap targets); wired into project `[id]/layout.tsx` as a sibling to `<main>` (fragment wrapper)
- `results/page.tsx` + `shortlist/page.tsx` — responsive: `md:hidden` cards, `hidden md:block` table; skeleton while loading
- `competitors/page.tsx`, `history/page.tsx`, `app/(app)/page.tsx` — skeleton loaders replace «Загрузка…»; all errors → `addToast`; designed empty states with lucide icons (FolderOpen, Users)
- `results-table.tsx` — `TextExpandCell` taps the text itself; ⊞ expand button removed
- `frontend/messages/ru.json` — `ResultsCards` namespace (21 keys); `Projects.emptyHint`
- No new ENV vars
**Smoke test:** DEFERRED — full 375px flow requires DEV login credentials (connect to https://web-dev-99e3.up.railway.app after CI deploys; verify bottom tabs, card results, sort sheet, toasts, skeletons, desktop table unchanged)
**Promoted to backlog:** none

## [E12-S1] Design system re-skin (light theme v1)
**Completed:** 2026-07-19
**Handover:**
- `globals.css` — full D28 `@theme` palette: `--color-bg/card/ink/secondary/accent/accent-soft/success/warning/danger/border`; `--radius-card/control/chip`; `--font-sans` (Golos Text) / `--font-display` (Unbounded)
- Root `layout.tsx` — loads Golos Text + Unbounded via `next/font/google`, body has `bg-bg text-ink font-sans`
- `frontend/components/ui/index.tsx` — Button (4 variants), Card, Input, Textarea, Badge (4 variants)
- `lucide-react` ^1.25.0 added as frontend dependency (D28); replaces all emoji glyphs across results-table, shortlist, history pages
- All `dark:` classes eliminated (grep-confirmed zero); all screens: login/register, projects home, project tabs (competitors/results/shortlist/history), run dialog, usage, admin
- Token classes: `bg-bg`, `bg-card`, `bg-accent`, `text-ink`, `text-secondary`, `text-accent`, `text-danger`, `text-success`, `text-warning`, `border-border`, `rounded-card`, `rounded-control`, `rounded-chip`
**Smoke test:** DEFERRED — local browser PASSED at 375px + 1280px (violet accent, tinted bg, Golos Text, Unbounded logo, lucide icons, no dark surfaces); DEV deploy pending CI on push to main (https://web-dev-99e3.up.railway.app)
**Promoted to backlog:** none

## [E4-S3] Claude cost optimization — 2026-07-19
**Handover:**
- Image resize: `settings.summary_image_max_side` (default 512, was 1024); `_fetch_image_block` accepts optional `settings` param
- Skip image: `_build_content_blocks` omits image when `len(caption) > settings.summary_skip_image_caption_chars` (default 200)
- Cross-run reuse: `_reuse_summary_if_available(session, item, project_id, run_id)` copies summary from most recent prior same-project same-external_id item; `summarize_run_items` accepts optional `project_id`; worker passes `run.project_id`
- Batch path: `_summarize_via_batches` triggered when pending items ≥ `summary_batch_threshold` (default 20); polls `client.messages.batches.retrieve()` until `processing_status == "ended"`, iterates `await client.messages.batches.results(id)` with `custom_id = str(item.id)` mapping; exception → falls back to concurrent path
- 6 new tests in `backend/tests/test_summarizer.py`; 4 prior tests still pass
**Smoke test:** DEFERRED — run same DEV project twice back-to-back; second run's Claude token usage should be a small fraction of first (reuse working); summaries remain correct Russian descriptions.

## [E7-S4] Pilot security guardrails — 2026-07-19
**Handover:**
- Invite code gate: `REGISTRATION_INVITE_CODE` env var; `GET /auth/register/config` returns `{require_invite: bool}`; register handler checks with `hmac.compare_digest`; frontend register page shows invite field conditionally
- Per-user run quota: `MAX_RUNS_PER_USER_PER_DAY` (default 10); counted in UTC day window; 429 with Russian message naming the limit
- Rate limiting: `backend/src/middleware/rate_limit.py` → `check_rate_limit(request, limit=10)` uses Redis INCR+EXPIRE; wired to login and register
- Boot check: `main.py` crashes at startup if `jwt_secret` == insecure default in non-local env
- Security headers: `_SecurityHeadersMiddleware` on API (X-Content-Type-Options, Referrer-Policy); CSP `frame-ancestors` on Next.js (`frame-ancestors 'self' https://web.telegram.org https://*.telegram.org`)
- XLSX formula injection: `_safe_text()` prefixes `=`, `+`, `-`, `@` cells with `'`; applied to account_handle, title, summary
- Login timing: `dummy_verify()` in `passwords.py` (rounds=12); called from `providers.py` on user-not-found path
- Tests: `backend/tests/test_guardrails.py` — 10 tests (3 unit tests pass locally without Postgres; 7 DB tests run in CI)
**Smoke test:** DEFERRED — requires DEV deploy (CI push sent); on DEV verify register without invite code fails with Russian message, 11th run is blocked with 429, hammering login returns 429, XLSX cell starting with `=` exports as text.

## [E#-S#] Title — YYYY-MM-DD
- What shipped
- Deviations from AC (if any)
- Handover notes for the next story

---

## [E3-S6] Worker resilience and parallel scraping — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `WorkerSettings.job_timeout = get_settings().worker_job_timeout_secs` (default 3600); arq now cancels stalled jobs automatically
- `process_run` catches `asyncio.CancelledError` (BaseException) separately: marks run `failed` with «Превышено время выполнения», commits via `asyncio.shield`, re-raises — previously `except Exception` silently swallowed it, leaving the run stuck
- Parallel scraping: accounts fetched concurrently under `scrape_concurrency` semaphore (default 5) via `asyncio.gather`; DB writes happen sequentially in the parent task after gather (AsyncSession is single-task-only)
- Idempotent insert: `pg_insert(ContentItem).on_conflict_do_nothing(index_elements=["run_id", "external_id"])` — re-delivered arq jobs cannot create duplicate content_items
- Migration `e5a3f2c9b1d7`: unique constraint `uq_content_items_run_id_external_id` on `content_items(run_id, external_id)`
- `summarize_run_items` accepts optional `client: AsyncAnthropic | None` and `http_client: httpx.AsyncClient | None`; worker creates both once per run and passes in — eliminates per-batch/per-image client recreation
- `Settings`: `worker_job_timeout_secs` (default 3600), `scrape_concurrency` (default 5)
- 3 new tests in `test_worker.py`: cancellation marks failed, parallel scrape correct row count, duplicate insert no-op
**Smoke test:** DEFERRED — requires DEV run with 8+ accounts; confirm wall time < sequential sum and no duplicate content_items on re-enqueue.
**Promoted to backlog:**
- None

---

## [E7-S2] Admin usage view — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `GET /admin/usage?from=&to=` → `AdminUsageOut` (users: list[UserUsageRow]) — `backend/src/api/admin.py`; 403 for non-admins
- `UserUsageRow`: user_id, email, runs, apify_units, claude_input_tokens, claude_output_tokens, total_cost_usd — sorted by cost desc
- `is_admin` on `User` model was already in the initial schema; `GET /auth/me` exposes it via `UserOut.is_admin`
- `frontend/app/(app)/admin/page.tsx` — month-range picker, per-user usage table, client-side redirect for non-admins
- Admin nav link in `frontend/app/(app)/layout.tsx` — shown only when `user.is_admin`
- `api.getAdminUsage(from, to)` + `AdminUsageResponse`/`UserUsageRowResponse` in `frontend/lib/api.ts`
- 5 tests in `backend/tests/test_admin.py` (403 non-admin, empty window, shows all users, response shape, is_admin in /me)
- No ENV vars added
**Smoke test:** DEFERRED — requires setting `is_admin=true` on a DEV user directly in Postgres, then visiting `/admin` on DEV.
**Promoted to backlog:**
- None

---

## [E7-S1] Usage rollups — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `GET /me/usage?from=&to=` → `UsageOut` (by_kind[], total_cost_usd) — `backend/src/api/usage.py`
- `KindTotal`: kind, quantity, cost_usd — all internal USD, trivially removable from responses for D26
- `frontend/app/(app)/usage/page.tsx` — current-month table; "Использование" link in app header
- `api.getMyUsage(from, to)` + `UsageResponse`/`KindTotalResponse` in `frontend/lib/api.ts`
- 5 new endpoint tests in `backend/tests/test_usage.py`; schema was already correct (no migration)
- No ENV vars added
**Smoke test:** PASSED — On DEV: navigated to `/usage`, page showed Результаты Apify (8) $0.0800, Входящие токены Claude (1 162) $0.0012, Исходящие токены Claude (94) $0.0005, Итого $0.0816. Header "Использование" link present and functional.
**Promoted to backlog:**
- None

---

## [E6-S2] Run and shortlist history — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `GET /projects/{project_id}/history/shortlist` → `list[ShortlistHistoryItemOut]` (all events, active + removed, newest first) — `backend/src/api/history.py`
- `ShortlistHistoryItemOut`: id, content_item_id, account_handle, type, title, url, added_at, removed_at
- Run history reuses existing `GET /projects/{project_id}/runs`
- `frontend/app/(app)/projects/[id]/history/page.tsx` — renders both tables; "Открыть результаты" → `router.push(/results?run={id})`
- Deep-link fix: `window.location.search` is read inside `loadRuns()` (runs in `useEffect`, always client-side) — avoids SSR-null problem with `useState` initializer
- `backend/tests/test_history.py` — 5 tests; `frontend/messages/ru.json` — `History` namespace
- No ENV vars added
**Smoke test:** PASSED — On DEV: opened История tab, 2 runs shown; clicked "Открыть результаты" on the older run (09:08, 6 items) → navigated to Результаты with `?run=625855e4-...`; run selector showed 09:08:35 run and 6 items rendered. Shortlist history shows 2 events with correct added_at/removed_at. Failed run error message truncation confirmed in UI.
**Promoted to backlog:**
- None

---

## [E6-S1] Shortlist — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `POST /projects/{project_id}/shortlist` — bulk add (idempotent: restores soft-deleted, skips active); `DELETE /projects/{project_id}/shortlist/{content_item_id}` — soft-delete via `removed_at`; `GET /projects/{project_id}/shortlist` — list active (`backend/src/api/shortlist.py`)
- `ShortlistItem` model + Alembic migration; partial unique index `uq_shortlist_items_active` on `(project_id, content_item_id) WHERE removed_at IS NULL`
- `in_shortlist: bool` on `ContentItemOut` / `ContentItemResponse` via correlated subquery in `GET /runs/{run_id}/items`
- `frontend/components/results-table.tsx` — ★/☆ toggle per row + select-all checkboxes + bulk add bar
- `frontend/app/(app)/projects/[id]/shortlist/page.tsx` — full shortlist tab (columns: account, добавлено, тип, заголовок, ссылка, описание, лайки, просмотры, убрать); "Создать сценарий" disabled with tooltip "Скоро"
- `backend/tests/test_shortlist.py` — 6 tests covering add/list/idempotent/remove/re-add/in_shortlist flag
**Smoke test:** PASSED — On DEV (`https://web-dev-99e3.up.railway.app/projects/082ae7c5-.../results`): clicked ☆ on 2 rows → both turned ★; opened Шорт-лист tab → both items appeared; clicked Убрать on row 1 → removed; returned to Результаты → row 1 shows ☆, row 2 still shows ★.
**Promoted to backlog:**
- None

---

## [E5-S2] XLSX export — 2026-07-18
**Completed:** 2026-07-18
**Handover:**
- `GET /runs/{run_id}/export.xlsx?sort=&order=` — `backend/src/api/export.py`; all rows, openpyxl workbook, frozen header
- `backend/src/services/xlsx_export.py` — `build_xlsx()` helper; URL column as hyperlinks; tz-aware datetimes stripped for Excel compat
- "Экспорт в Excel" button added to results page toolbar (`frontend/app/(app)/projects/[id]/results/page.tsx`); only visible when a done run with items is selected
- `api.downloadRunXlsx(runId, sort, order)` in `frontend/lib/api.ts` — blob fetch → programmatic `<a download>` click
- RFC 5987 `filename*=UTF-8''<percent-encoded>` used in `Content-Disposition` to handle Cyrillic project names (bug found+fixed during smoke test)
**Smoke test:** PASSED — Curl'd `GET /runs/{id}/export.xlsx` on DEV with browser token; HTTP 200; `content-disposition: attachment; filename*=UTF-8''content-scout_%D0%9A%D0%BE%D0%BD%D0%BA%D1%83%D1%80%D0%B5%D0%BD%D1%82%D0%BD%D1%8B%D0%B9_%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D0%B7_2026-07-18.xlsx`; openpyxl validation: sheet "Результаты", 8 rows (7 data), Russian headers, real hyperlink on URL cell.
**Promoted to backlog:**
- None

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
