# DONE — content-scout

Completed stories land here, newest first. Format:

## [E14-S1] Scheduled runs: schema and migration
**Completed:** 2026-07-22
**Handover:**
- `backend/src/models/scheduled_run.py:ScheduledRun` — mirrors `AnalysisRun`'s XOR `duration_days`/`item_limit` CHECK constraint (`duration_or_item_limit_range`, from E3-S7) plus a new `day_of_week_range` CHECK (0=Monday..6=Sunday, matching Python's `datetime.weekday()`). `timezone` is a plain IANA-name `String(64)` — no new dependency, Python 3.12 stdlib `zoneinfo` resolves it in E14-S2's cron tick — with a Python-side default `"Europe/Moscow"`. `last_run_id` is a nullable FK to `analysis_runs.id`, to be updated by E14-S2's dispatcher after each fire.
- Migration `f6a7b8c9d0e1` (now head, follows `a9b8c7d6e5f4`); single linear chain confirmed via `alembic heads`.
- `make_scheduled_run()` test helper added to `backend/tests/conftest.py`, same shape/pattern as the existing `make_run()`.
- 4 new tests in `backend/tests/test_models.py`: roundtrip + defaults, XOR-rejected, both-set-rejected, day_of_week-out-of-range-rejected. `ruff format`/`ruff check`/`mypy src` clean.
- **For E14-S2:** table is ready — the CRUD API + arq cron tick build directly on top of `ScheduledRun`.
**Smoke test:** DEFERRED — needs the migration applied on a real DEV Postgres; confirm `\d scheduled_runs` shows the expected columns and both CHECK constraints (same deferral pattern as the rest of this project's DB-touching stories — no local Postgres in this sandbox).
**Promoted to backlog:** none

## [Post-Sprint-8 fix] Results/Details landing-page swap
**Completed:** 2026-07-22
**Handover:**
- Direct user feedback after E13-S2/E15-S3 shipped: the intended landing page for Результаты was always the run list (create-run button + run history), not an item table — and clicking a run should go straight to the E15-S3 run-detail page, not filter an item table by `run_id`.
- `frontend/app/(app)/projects/[id]/results/page.tsx` — replaced entirely. Now shows the "Создать запуск" button + run-history cards (moved verbatim from `details/page.tsx`, E13-S2), with each done run card navigating to `/projects/[id]/runs/[runId]` instead of `/results?run=<id>`. The old item-table/run-selector logic that used to live here is fully superseded by the E15-S3 run-detail page's Publications tab (which already reused `listProjectItems` scoped to one run — nothing was lost).
- `frontend/app/(app)/projects/[id]/details/page.tsx` — trimmed back down to just the KPI card + Конкуренты/Запланированные запуски nav links; the create-run button and run-history block moved out.
- `frontend/app/(app)/projects/[id]/runs/[runId]/page.tsx` — back link now reads "← Результаты" → `/projects/[id]/results` (was "← Детали" → `/projects/[id]/details`).
- `frontend/app/(app)/layout.tsx` — the run-notifications dropdown now routes tracked runs straight to `/projects/[id]/runs/[runId]` (was `/results?run=<id>`, which no longer does anything useful now that Результаты doesn't read that query param).
- `frontend/components/ui/bottom-nav.tsx` + `frontend/app/(app)/projects/[id]/layout.tsx` — the Результаты tab (mobile bottom nav + desktop tab bar) now stays highlighted while viewing a run-detail page (`pathname.includes("/runs/")`), and the page heading shows "История запусков" for both `/results` and `/runs/[runId]`.
- `frontend/messages/ru.json` — moved `createRunButton`/`cardAccounts`/`cardItems` from `Details` to `ResultsTable`; dropped the unused/buggy `cardTokens` key (it displayed `progress_items` under a "Токены" label, duplicating `cardItems` — a pre-existing copy-paste bug in the original E13-S2 code, not a new one); `RunDetail.backToDetails` renamed to `backToResults`; `ProjectShell.sectionResults` changed from "Публикации конкурентов" to "История запусков".
- The orphaned `frontend/app/(app)/projects/[id]/history/page.tsx` (unreachable since E13-S1 removed its nav link) still references the old `/results?run=...` pattern — left untouched since it's dead code outside this fix's scope; flagging again as a cleanup candidate (see BACKLOG.md's E13-S2 handover for the original flag).
- `tsc --noEmit` and `next lint` both clean. Verified visually via a temporary `frontend/app/dev-preview` scratch route (mocked `window.fetch`), screenshotted the new Результаты landing page rendering the run list + create button correctly — deleted before commit. The click-through into an individual run detail page could not be reliably exercised end-to-end in this sandbox (an auth-state race between the mocked fetch and this app's Telegram-webview auto-login path repeatedly logged the scratch session out specifically on that nested dynamic route, in a way unrelated to this change's actual diff — the run-detail page's own rendering logic is unchanged from E15-S3's already-verified version, only its back-link target/label were touched here).
**Smoke test:** DEFERRED — needs a real DEV project to confirm the Результаты run list renders, create-run works from there, and clicking a run lands on its detail page (same deferral pattern as the rest of this project's verification; count of deferred smoke tests across this file is now well past the 5+ flag threshold — see session summary).
**Promoted to backlog:** delete the orphaned `/history` route (dead code since E13-S1; flagged repeatedly, never actioned)

## [E15-S3] Run detail page: Summary + Publications tabs
**Completed:** 2026-07-22
**Handover:**
- New route `frontend/app/(app)/projects/[id]/runs/[runId]/page.tsx` with local tab state (Summary/Publications), replacing the ad-hoc "click a history row to filter Результаты" pattern. Existing project-wide Результаты tab is untouched.
- Extended `RunOut`/`GET /runs/{id}` (`backend/src/api/runs.py`) with `summary_status`/`summary_text`/`summary_topics` — E15-S1 stored these but never exposed them via the API; this story added that exposure.
- Publications tab deliberately reuses `GET /projects/{id}/items?run_id=...` (`listProjectItems`) rather than the run-scoped `GET /runs/{id}/items`, because only the former supports `starred_only` — gives full sort/star/export parity with zero new backend surface, `run_id` just pinned. Run-filter icon removed by passing `runs={[]}` to `ResultsControlsBar` (already suppresses the icon internally) — `results-controls.tsx` itself untouched.
- Top-5-by-virality cards on the Summary tab are clickable, switching to the Publications tab (the AC's "linking into" requirement).
- `telegram_notify.py`'s completion DM now links to `/projects/{project_id}/runs/{run.id}` instead of `/results?run=...`.
- 2 new backend tests (`test_runs.py`) + 1 tightened assertion (`test_telegram_notify.py`); `ruff format`/`ruff check`/`mypy src` clean; frontend typecheck/eslint clean. Verified via a temporary scratch route with a mocked `fetch` (this page does live API calls, not props, so the mock exercised the real page end-to-end): done/failed/pending summary states, non-done gating, top-5→Publications navigation, run-filter icon absence — desktop + 375px, no console errors, deleted before commit.
- **This closes Sprint 8** — all three epics (E13, E16, E15) done. Next up: Sprint 9 (E14 scheduled runs).
**Smoke test:** DEFERRED — needs a real DEV project with a finished run to confirm the Summary tab's live data, Publications-tab parity with Результаты minus the run-filter icon, and a real Telegram completion DM's link.
**Promoted to backlog:** none

## [E15-S2] Top-5-posts-by-virality for a run
**Completed:** 2026-07-22
**Handover:**
- New `GET /runs/{run_id}/top-virality?limit=5` (`backend/src/api/items.py:list_top_virality_items`, `TopViralityOut`) — reuses `ContentItemOut` shape and the existing `virality_baseline_subquery`/`virality_ratio_expr` join from `list_run_items`, filtered to non-null ratios (excludes insufficient-sample items entirely) and ordered desc with a configurable `limit` (1–20, default 5).
- A dedicated endpoint rather than folding into E15-S1's run-summary storage (that story stores fields on `AnalysisRun`, not an endpoint) or the paginated `/runs/{run_id}/items` (different, non-paginated shape).
- 3 new tests in `test_items_api.py`. `ruff format`/`ruff check`/`mypy src` clean. No new dependencies, no ENV vars, no migration.
- **For E15-S3:** this endpoint plus E15-S1's stored summary fields are both ready to consume for the run detail page's Summary tab.
**Smoke test:** DEFERRED — needs a real finished DEV run with ≥5 qualifying items to confirm the returned top-5 matches manually sorting the Publications tab by virality descending.
**Promoted to backlog:** none

## [E15-S1] Run-level AI summary generation
**Completed:** 2026-07-22
**Handover:**
- Chose a JSON-column-on-`AnalysisRun` design over a separate `run_summaries` table (the AC explicitly said to pick whichever avoids a join for the common read path — E15-S3's run detail page already loads the `AnalysisRun` row).
- `RunSummaryStatus` enum (`pending`/`done`/`failed`) + `AnalysisRun.summary_status`/`summary_text`/`summary_topics`/`summary_generated_at` — migration `a9b8c7d6e5f4` (now head).
- `backend/src/services/run_summary.py:generate_run_summary(session, run, *, user_id, client=None)` — one Claude call (reusing `settings.summary_model`) synthesizing a RU overview + top-5 topics from the run's item summaries/captions (capped at 150 items, newest first); `parse_summary_response()` is a pure, independently-tested function for the `РЕЗЮМЕ:`/`ТЕМЫ:` text protocol. Never raises: no items / API error / unparseable response all resolve to `summary_status=failed` (or `done` with the raw text as a fallback for the unparseable case) without failing the run — mirrors `notify_run_complete`.
- Wired into `worker.py:process_run` right before the run is marked done, reusing the already-open Claude/HTTP clients from per-item summarization; records one input+output `usage_events` pair per run (same pattern as every other Claude call site in this codebase).
- `docs/PROMPTS.md` gained the "Run summary (E15-S1)" prompt.
- **For E15-S3:** these fields have no API exposure yet (out of this story's scope) — the run-detail page will need to add them to `RunOut` or a new run-detail endpoint.
- 11 new tests in `test_run_summary.py` (3 pure-function + 5 DB-integration + parsing edge cases); `ruff format`/`ruff check`/`mypy src` clean; `alembic heads` confirms a single linear chain. No new dependencies, no ENV vars.
**Smoke test:** DEFERRED — needs a real finished DEV run to confirm a plausible Russian summary + top-5 topics land within normal completion time and exactly one input+output usage_events pair is recorded.
**Promoted to backlog:** none

## [E16-S1] Analysis teaser page
**Completed:** 2026-07-22
**Handover:**
- By the time this story started, E13-S1 had already deleted `/create` and stubbed `/analysis` (Sparkles "coming soon"), so the story's originally-listed "read `create/page.tsx`" file no longer existed — read the current `/analysis` stub directly instead. No functional impact.
- `frontend/app/(app)/projects/[id]/analysis/page.tsx` — kept the Sparkles/title/comingSoon block, added a 3-card responsive grid (shared `Card`/`Badge` components) for Разбор конкурента / Разбор запуска / Разбор публикации (the last covers "publication deep-dive + script generation" as one card, matching the existing `comingSoon` copy which already describes it as combined). All cards `opacity-60` + `cursor-not-allowed` + `aria-disabled`, "Скоро" badge, zero click handlers.
- `frontend/messages/ru.json` — `Analysis.cards.{badge,competitor,run,publication}` keys added.
- No backend changes, no new deps, no ENV vars. This closes Sprint 8's E16 epic — E15-S1/S2/S3 (run detail: AI summary, top-5-by-virality, Summary+Publications tabs) are next.
- typecheck + eslint (the CI gate) both clean. Verified visually via a temporary `frontend/app/dev-preview/analysis` scratch route (direct import of the real page component), screenshotted at desktop + 375px, deleted before commit.
**Smoke test:** DEFERRED — needs a real DEV project open on the Анализ tab to confirm the live cards render with no console errors (same deferral pattern as the rest of this project's verification).
**Promoted to backlog:** none

## [E13-S3] Competitors page trim
**Completed:** 2026-07-22
**Handover:**
- `frontend/app/(app)/projects/[id]/competitors/page.tsx` — removed `selected`/`runDialogOpen` state, `toggleSelected`/`toggleSelectAll`, the select-all header row, per-row checkboxes, the "Запустить анализ" button, and the `RunDialog` import/render entirely. Run creation lives only on Детали now (E13-S2).
- Added a "← Детали" back link at the top of the page.
- `Competitors.infoExplanation` (50-cap info popover) rewritten to drop references to the removed selection/run flow; `runButton`/`selectAll`/`selectedCount` message keys removed as dead, `backToDetails` added.
- Add/remove competitor flow, avatar/name/followers row display (E2-S3), and the 3-dot delete menu are unchanged.
- No frontend unit test suite exists in this repo; typecheck + eslint (the CI gate) both clean. Verified visually via a temporary `frontend/app/dev-preview/competitors` scratch route with mock data, screenshotted at 375px, deleted before commit.
- This closes Sprint 8's E13 epic (nav restructure: E13-S1/S2/S3). E16-S1 and E15-S1/S2/S3 remain backlog — out of scope for this session, which was limited to "E13 all stories."
**Smoke test:** DEFERRED — needs a real DEV project to confirm the trimmed page end-to-end (same deferral pattern as the rest of this project's Apify-dependent verification).
**Promoted to backlog:** none

## [E13-S2] Details dashboard: KPI card, nav links, run-history cards, create-run entry
**Completed:** 2026-07-22
**Handover:**
- New `GET /projects/{project_id}/stats` (`backend/src/api/projects.py`, `ProjectStatsOut.lifetime_items_analyzed`) — `SUM(AnalysisRun.progress_items)` across all runs for the project, any status, via `func.coalesce(..., 0)`; scoped through the existing `_get_owned_project` 404 pattern. `frontend/lib/api.ts`: `ProjectStatsResponse` + `api.getProjectStats`.
- `frontend/app/(app)/projects/[id]/details/page.tsx` replaces the E13-S1 placeholder: KPI card (competitors count from the existing accounts list + lifetime items from the new stats endpoint, 2-column grid built to add more stats without a layout change), full-width nav rows to Конкуренты and Запланированные запуски (`/scheduled` — 404s until E14-S3 ships, expected), run-history cards (date/accounts/publications/tokens, clickable to `/results?run=<id>` only when `status === "done"`), and a "Создать запуск" button opening the existing `RunDialog` against the whole active account list (`accountIds: undefined` — per-run selection is gone as of E13-S3).
- "Tokens consumed" reuses `progress_items` directly — 1 token is debited per scraped publication in this system (`worker.py`), so it's the same number as "publications analyzed", not a separately tracked field.
- New tests: `test_project_stats_sums_items_across_runs`, `test_project_stats_zero_with_no_runs`, `test_project_stats_scoped_to_workspace` in `backend/tests/test_projects.py`. ruff/mypy/tsc/next-lint all clean locally; pytest itself needs the CI Postgres service (no local DB in this sandbox, consistent with every prior story here).
- `/history` route (run table + shortlist history) is unchanged and now partially redundant with Детали's run cards — flagged as a cleanup candidate once E15-S3 (run detail view) exists and nothing links to `/history` anymore.
**Smoke test:** DEFERRED — needs a real DEV project with at least one finished run to confirm KPI counts, nav links, and run-card data end-to-end (same deferral pattern as the rest of this project's Apify-dependent verification). Verified locally via a temporary `frontend/app/dev-preview/details` scratch route with mock data, screenshotted at desktop + 375px, deleted before commit.
**Promoted to backlog:** none

## [E13-S1] Bottom nav restructure: Детали / Результаты / Анализ
**Completed:** 2026-07-22
**Handover:**
- `frontend/components/ui/bottom-nav.tsx` and the desktop tab bar in `frontend/app/(app)/projects/[id]/layout.tsx` both now render exactly Детали (`LayoutDashboard`) / Результаты (`BarChart2`) / Анализ (`Sparkles`), in that order.
- Root project route `/projects/[id]` now redirects to `/projects/[id]/details` (was `/competitors`).
- `/projects/[id]/create` deleted. Two new stub routes take its place in the nav: `/projects/[id]/analysis` (Sparkles "coming soon" pattern — reuses the exact visual the old `/create` page used; `Analysis` message namespace) and `/projects/[id]/details` (bare placeholder for now; `Details` message namespace). E16-S1 will flesh out `/analysis` with the real teaser cards; E13-S2 (next, same session) replaces `/details` with the full dashboard.
- `sectionHeading()` in the shared layout now branches on `/details` and `/analysis`; the dead `/create` branch and `sectionCreate` key are gone.
- Incidental fix: `ProjectShell.tabResults` previously said "Анализ" while pointing at the `results` segment (a naming leftover) — now correctly says "Результаты".
- No backend changes. No frontend unit test suite exists in this repo (CI gate is typecheck + eslint per CONVENTIONS.md); both pass. Verified visually via a temporary `frontend/app/dev-preview/nav` scratch route (mounted the real nav components with mock props, screenshotted desktop + 375px, deleted before commit) — same pattern as E12-S3, since this sandbox has no local Postgres/DEV login.
**Smoke test:** DEFERRED — needs a real DEV project open on desktop and 375px to confirm the live nav end-to-end (same deferral pattern as the rest of this project's Apify/Telegram-dependent verification).
**Promoted to backlog:** none

## [E12-S3] Mobile results controls consolidation + polish
**Completed:** 2026-07-22
**Handover:**
- Shipped as direct fixes/polish during the Sprint 7 session, no story ID at the time — backfilled into BACKLOG.md/DONE.md during the 2026-07-22 execution-plan session per the sprint-review "untracked fixes" check.
- `frontend/components/results-controls.tsx` (new) replaces three separate mobile control rows (run-selector, token-warning, sort+export) with one icon row: sort (bottom sheet), export (bottom sheet, includes the Telegram-downloads-folder note via `canDownloadViaTelegram()`), run-filter (bottom sheet + "все запуски"), star (shortlist-only, respects the active run filter). Sort/filter/star grouped left, export pushed right (`ml-auto`).
- Все/Отмеченные tabs removed from `results/page.tsx` — the star filter supersedes them; unused `SubTab` state, `shortlistContent` block, and related handlers deleted. Orphaned `/projects/[id]/shortlist/page.tsx` was flagged (not fixed) as dead code, separate cleanup task.
- `backend/src/services/metrics.py:virality_ratio_expr(median_engagement, median_views, item_count, settings)` — SQL-level virality ratio (reuses `virality_baseline_subquery`), wired into `sort_columns` in both `api/items.py` and `api/export.py` so "Виральность" is a real sort option, not just a display bucket. "Вовлечённость"/"Комментарии" added as sort options too.
- `frontend/lib/format.ts:VIRALITY_STYLE` — medium recolored grey→soft yellow (`bg-warning/10 text-warning`), low grey→soft red (`bg-danger/10 text-danger`); high stays green. Both were indistinguishable grey chips before.
- `results-cards.tsx` — days-since-publication chip now only renders when a card is expanded (`{expanded && (...)}`), decluttering collapsed cards.
- Verified via temporary `frontend/app/dev-preview/**` scratch routes (mounted the real components with mock data, screenshotted via the Browser pane, then deleted before committing — no local Postgres or DEV login credentials available in this sandbox).
- Commits: `b955fba` (single-row collapse), `9468564` + `7679080` (tabs removal, colors, sort options, export copy; second commit fixed a CI-only stale-constraint-name test assertion left over from E3-S7, unrelated to this story's own logic). CI green including `deploy-dev` on both.
**Smoke test:** DEFERRED — needs a real finished DEV run to eyeball on a phone/Telegram webview (same deferral pattern as the rest of Sprint 7).
**Promoted to backlog:** none

## [E3-S7] Run scope: last-N-publications mode
**Completed:** 2026-07-22
**Handover:**
- Shipped alongside E12-S3 in the same commits, no story ID at the time — backfilled per the sprint-review "untracked fixes" check.
- `AnalysisRun.duration_days`/`.item_limit` both nullable, exactly one set, enforced by CHECK constraint `duration_or_item_limit_range` (migration `b8c4d5e6f7a1`, now head; downgrade backfills `duration_days=7` before restoring NOT NULL). Postgres `GREATEST`/`LEAST`-style null-handling isn't used here — this is a plain XOR CHECK, not the virality baseline pattern.
- `backend/src/services/estimator.py:estimate_run` is now keyword-only (`*, duration_days, item_limit`), branches `accounts_count × item_limit` vs. the existing duration calc.
- `Platform.fetch_content` is keyword-only `since: datetime | None, limit: int | None = None`; `InstagramPlatform` omits `onlyPostsNewerThan` and sets `resultsLimit = limit` directly in count mode; `MockPlatform` mirrors the branching for tests.
- `backend/src/api/runs.py:RunRequestIn` gained a `model_validator(mode="after")` enforcing exactly-one-of `duration_days`/`item_limit`, mirroring the DB constraint at the API layer.
- Found and fixed a real pre-existing-pattern bug in passing: `RunSummaryOut` in `api/usage.py` had non-optional `duration_days: int` — would have 500'd on any item_limit-mode run's usage listing. Now `int | None` + new `item_limit: int | None`.
- Frontend: `run-dialog.tsx` gained a day/count segmented toggle (`ITEM_LIMIT_OPTIONS = [5,10,15,20,30,50]`); `history/page.tsx`'s duration column now branches on which field is set ("N дней" vs "последние N публикаций").
- New tests: `test_estimator.py`, `test_instagram_platform.py`, `test_worker.py` (`test_process_run_item_limit_mode_fetches_last_n_publications`, via the existing `MockPlatform` path), `test_runs.py` (reject-both/reject-neither/accept cases), `test_models.py` (constraint tests, split into separate test functions per Postgres's transaction-abort-after-IntegrityError semantics — a single test can't run two `pytest.raises(IntegrityError)` blocks against the same session fixture).
- CI caught one real regression before this closed: after the constraint rename, a pre-existing test (`test_run_duration_check_rejected`) still matched the old constraint name — fixed in `7679080` with proper coverage added for the item_limit side.
- Commits: `9468564`, `7679080`.
**Smoke test:** DEFERRED — needs a real DEV run in count mode against public IG accounts (same deferral pattern as every other Apify-touching story).
**Promoted to backlog:** none

## [E5-S5] Virality score (High/Medium/Low) per publication
**Completed:** 2026-07-22
**Handover:**
- `backend/src/services/metrics.py` — `virality_ratio_expr()` (self-relative `performance_ratio` per item, SQL window functions: `percentile_cont(0.5).within_group(...).over(partition_by=account_id)` for the account's median engagement, and separately for reels' median views; `NULLIF`/`GREATEST` handle the zero-median and non-reel-item edge cases without crashing or fabricating scores); `account_item_count_expr()` (window function, backs the min-items guard); `engagement_rate_expr()` (per-row, needs `Account` joined); `bucket_virality(ratio, item_count, settings)` — deliberately a pure Python function (not SQL `CASE`) so the threshold/insufficient-sample logic is unit-testable without a database.
- `Settings.virality_high_ratio` (2.0) / `virality_low_ratio` (0.7) / `virality_min_items` (3) — tunable without a code change.
- `ContentItemOut.virality` / `.engagement_rate` added identically in both `api/items.py` (paginated) and `api/export.py` (full run, no pagination) — window functions compute over the whole `WHERE run_id = ...` result set in both cases regardless of `LIMIT`/`OFFSET`, per standard SQL evaluation order.
- `xlsx_export.py` — "Виральность" (Russian bucket label or blank) and "Вовлечённость" (raw fraction, `number_format="0.0%"` per cell) columns added.
- Frontend: `results-table.tsx` gets a badge column (inline-styled chip, not the shared `Badge` component — its variants didn't cleanly map to "success/neutral/muted") with a `title` tooltip, plus a sortable "Вовлечённость" column. `docs/UI_GUIDELINES.md`'s Results table section refreshed to match current reality (was stale from an earlier column removal) and carries the same self-relative clarification.
- 13 pure-Python tests (`test_metrics.py`) ran and passed locally without a DB; a full API test (`test_virality_badge_and_engagement_rate`) exercises a real median/outlier fixture plus an insufficient-items account; `test_export.py` updated. mypy + ruff + `tsc --noEmit` + `next lint` all clean.
- This closes Sprint 7 (all 5 stories from the 2026-07-21 single-blogger reprioritization) — next step is a `/sprint-review` to plan Sprint 8 from BACKLOG.md's post-MVP list.
**Post-close fix (CI unblocking — 2026-07-22):** the original implementation computed the per-account median via `percentile_cont(0.5).within_group(...).over(partition_by=account_id)` — a SQL window function. CI failed with `ERROR: OVER is not supported for ordered-set aggregate percentile_cont`: Postgres only allows ordered-set aggregates like `percentile_cont` in plain `GROUP BY` form, never as a window function — a gap this sandbox's lack of a local Postgres couldn't catch before pushing. Replaced with `metrics.py:virality_baseline_subquery(run_id)` (a `GROUP BY account_id` subquery joined back by account_id) plus a new pure-Python `virality_ratio()` function for the ratio math itself — which also meant the AC's "ratio computation against a fixed fixture" tests could move fully offline into `test_metrics.py` instead of needing a live DB. See BACKLOG.md's E5-S5 entry for the full writeup.
**Smoke test:** DEFERRED — requires a real finished DEV run with a mixed-type, ≥3-item account.
**Promoted to backlog:** none

## [E5-S3] Comments count column
**Completed:** 2026-07-22
**Handover:**
- `content_items.comments` has existed since E3-S2 (already scraped, never surfaced) — no migration needed for this story.
- `ContentItemOut.comments` added in both `api/items.py` and `api/export.py`; `"comments"` added to the `SortField` literal and `sort_columns` maps in both routers. `ContentItem` was already selected in full in both queries, so no new `select()` column was needed.
- `results-table.tsx` — new sortable "Комментарии" column placed right after "Лайки" (the desktop table has no `views` column today, removed in an earlier pass, so this is the closest equivalent to "near лайки/просмотры"). `frontend/lib/api.ts` `ContentItemResponse`/`ItemSortField` updated.
- `xlsx_export.py` — "Комментарии" header inserted after "Просмотры" (column 10 of 13 now).
- Scoped to desktop table + XLSX export only, per the story's file list — not added to mobile cards or the shortlist table/export.
- New `test_sort_by_comments_and_value_present` in `test_items_api.py`; shape assertion and `test_export.py` header/value assertions updated. mypy + ruff + `tsc --noEmit` + `next lint` all clean.
**Smoke test:** DEFERRED — requires a real finished DEV run; verify the column shows plausible counts, sorts correctly, and matches the XLSX export.
**Promoted to backlog:** none

## [E2-S3] Competitor profile enrichment
**Completed:** 2026-07-22
**Handover:**
- `ProfileInfo` (E5-S4) extended with `display_name`/`avatar_url`; `InstagramPlatform.fetch_profile` now maps Apify detail-response `fullName`→`display_name`, `profilePicUrl`/`profilePicUrlHD`→`avatar_url` alongside `followersCount`.
- New `src/worker.py:fetch_account_profile(ctx, account_id, user_id)` arq job — separate from the analysis-run lifecycle, since CONVENTIONS.md forbids external calls from routers. `POST /projects/{id}/accounts` enqueues one job per newly added account right after commit (`src/services/queue.py:enqueue_profile_fetch`); on failure the job returns silently, leaving the row's existing data (or just the handle) intact — never blocks add.
- `Account.display_name` / `Account.avatar_url` — migration `e4f5a6b7c8d9` (now head). Reused E5-S4's `followers_updated_at` as the shared "last profile fetch" timestamp for all three enriched fields rather than adding a second column.
- `AccountOut` gained `display_name`, `followers_count`, `avatar_url`, `profile_updated_at`.
- Frontend: Конкуренты list row now shows an avatar (Users icon fallback), display_name/@handle, ru-RU formatted followers, and a short "обновлено DD.MM" date; falls back to «нет данных» only when nothing has ever been fetched. Renamed the page's pre-existing unpopulated `follower_count` stub to `followers_count` and switched its formatter from "K"/"M" to the same "тыс."/"млн" style used in the Результаты table.
- 3 new tests in `test_profile_enrichment.py` (update on success, fallback-on-failure, missing-account no-op); `test_instagram_platform.py` and `test_accounts.py` updated. mypy + ruff + `tsc --noEmit` + `next lint` all clean.
**Post-close fix (CI unblocking — 2026-07-22):** `fetch_account_profile` originally did everything inline in the arq wrapper, opening its own session via `get_sessionmaker()`. This passed locally but failed in CI: the test called the wrapper directly, and the test fixture's session lives inside an outer transaction that's never really committed to Postgres, so a second, independently-opened connection couldn't see the test's own uncommitted account. Fixed by splitting it into `apply_profile_update(session, account, user_id)` (testable core, takes an already-open session) + `fetch_account_profile(ctx, account_id, user_id)` (thin arq wrapper) — the same split `process_run`/`run_analysis` already uses. Tests now call `apply_profile_update` directly with the injected session.
**Smoke test:** DEFERRED — requires a real DEV account add against a public IG profile; verify avatar/name/followers appear within a minute and the row stays usable if the fetch fails.
**Promoted to backlog:** none

## [E5-S4] Subscriber count next to account name
**Completed:** 2026-07-22
**Handover:**
- `src/platforms/base.py:ProfileInfo(followers_count)` — new dataclass; `Platform` Protocol gained `fetch_profile(account) -> ProfileInfo`. `MockPlatform.fetch_profile` returns a fixed `12_400`; `InstagramPlatform.fetch_profile` calls Apify with `resultsType: "details"` (vs. `"posts"` for content), sharing a new generic `_with_retries()` retry helper with `fetch_content`.
- `Account.followers_count` / `Account.followers_updated_at` — migration `d3e4f5a6b7c8` (now head, was `c2275f27bb18`). Updated by the worker once per account per run during the scraping phase; left untouched (falls back to the last known value) whenever the profile fetch fails, so a transient Apify error never blanks out a previously known count.
- `src/worker.py:process_run` — `_fetch_one` fetches profile + content per account under the same concurrency semaphore; a profile-fetch failure is caught and swallowed locally, never surfaces as an account failure and writes no usage event, while content scraping proceeds independently.
- `ContentItemOut.followers_count` (`api/items.py`, `api/export.py`) — joined from `Account.followers_count` in the existing results query, no extra round trip.
- `services/xlsx_export.py` — "Подписчики" column added right after "Аккаунт" (shifted every later column index by one, including the hyperlink cell for "Ссылка").
- Frontend: `results-table.tsx` (desktop) and `results-cards.tsx` (mobile — the Mini App's primary view) both show a ru-RU formatted follower count ("12,4 тыс.") under/next to the account handle via a small local `formatFollowers()` in each file.
- Noted for E2-S3 (next story): the Конкуренты page already has speculative frontend scaffolding (`AccountResponse.follower_count`, singular) from an earlier UI pass that the backend never populated — E2-S3 should rename it to `followers_count` to match this story's naming and wire it to the real `fetch_profile()` method instead of re-implementing the details fetch.
- 5 new backend tests (3 `InstagramPlatform.fetch_profile` unit tests, 2 worker tests for update + fallback-on-failure); `test_items_api.py`/`test_export.py`/`test_worker.py` updated for the new field/column. mypy + ruff clean; frontend `tsc --noEmit` + `next lint` clean.
**Smoke test:** DEFERRED — requires a real DEV run against public IG accounts (same deferral pattern as every other Apify-touching story in this project); verify a row's account name shows a plausible follower count and `usage_events` gains one extra `apify_result` row per account.
**Promoted to backlog:** none

## [E8-S6] Telegram Mini App auto-login bootstrap fix
**Completed:** 2026-07-22
**Handover:**
- Root cause: Telegram never auto-injects `window.Telegram.WebApp` into the Mini App webview — the page has to load Telegram's own `telegram-web-app.js` SDK script itself. This codebase only ever loaded `telegram-widget.js` (the unrelated Login *Widget* script). Fixed by loading `telegram-web-app.js` via `next/script` (`beforeInteractive`) in `frontend/app/layout.tsx`; `suppressHydrationWarning` added to `<html>` since the script mutates `document.documentElement.style` on load.
- Confirmed live: user opened the Mini App from the bot on a real phone and drove an extended real session with zero manual login — the only issues reported afterward were UI/UX bugs *inside* an already-authenticated session, which is itself the proof the bootstrap fix held.
- That real-device pilot session surfaced 5 UI bugs + 1 production incident, all fixed same-session in untracked commits (`e20e5ed`, `0055313`, `07c2b9a`, `e8dbae8`) rather than pre-planned story ACs:
  - No way to exit/log out of the Mini App, and no account name shown → added `users.display_name` (editable in Settings, random `Пользователь####` default on registration, migration `c2275f27bb18`) and a real `telegramLogout()` (soft-logout via a `content-scout-tg-logged-out` localStorage flag, since Telegram itself has no sign-out signal to react to). Post-logout `/login` renders the full standard page (email/password form + register link), with only the Telegram half swapped for a direct one-tap sign-in button instead of the (redirect-only) Login Widget script.
  - Run dialog blocked the rest of the app while a run was in progress, and only one run could be tracked at a time → new `frontend/lib/run-tracker.tsx` (`RunTrackerProvider`/`useRunTracker`) polls tracked runs independently of any dialog, persists lightweight refs to `localStorage`, and supports multiple parallel runs; `run-dialog.tsx` is now always closable/minimizable; a header bell (`frontend/app/(app)/layout.tsx`) shows unseen-run badges.
  - Analysis runs silently got stuck in "Превышено время выполнения" → root-caused to Apify's Pay-Per-Event pricing: `maxTotalChargeUsd` defaults to the account's *entire remaining monthly balance* when not set explicitly, so concurrent runs' implicit reservations could exceed the real remaining balance and deadlock in `READY`. Fixed by capping it per-fetch (`Settings.apify_max_charge_per_fetch_usd`, default `$0.5`) in `backend/src/platforms/instagram.py`, plus treating any non-`SUCCEEDED` terminal Apify run status as a failure instead of silently continuing. Note: an Apify platform-wide DB-degradation incident was also active that day and likely contributed to the specific stuck runs seen live — the cap fix is a real, worth-keeping bug fix independent of that outage.
  - Minor polish: `BottomSheet` top padding fixed (shared component, was touching titles), competitors page decluttered (removed redundant "1/50" + "Добавлено: N" counters, added an info-icon popover explaining the 50-account cap and workflow).
- None of the above was pre-scheduled backlog work; each was a direct fix to a bug the user hit live. Flagged in BACKLOG.md's E8-S6 handover since several of these files are also touched by the still-open E5-S3/E5-S4/E2-S3/E5-S5 stories.
**Smoke test:** PASSED (real Telegram account, live pilot session) — see Handover.
**Promoted to backlog:** none

## [E8-S2] Telegram bot notifications
**Completed:** 2026-07-19
**Handover:**
- `backend/src/services/telegram_notify.py`: `notify_run_complete(run, user)` — Bot API DM on run done/failed; skips if no token or no telegram_id; all exceptions swallowed
- `worker.py`: notify called after done commit + in both except paths (CancelledError, generic); notification failure never surfaces to caller
- `UserOut` + `UserResponse`: added `has_telegram: bool`
- `frontend/app/(app)/settings/page.tsx`: shows TG link status; Telegram Login Widget to link (calls `POST /auth/telegram/link`); updates `linked` state on success
- App header (`(app)/layout.tsx`): «Настройки» nav link added
- 5 unit tests in `test_telegram_notify.py` — all pass without DB
**Post-close fixes (CI unblocking — 2026-07-19):**
- `src/api/auth.py` `TelegramLoginIn`: optional fields changed `str=""` → `str|None=None` so `model_dump(exclude_none=True)` omits absent fields from the HMAC check string (hash verification was failing for login widget payloads without last_name/username/photo_url)
- `src/main.py` `_SecurityHeadersMiddleware`: replaced `BaseHTTPMiddleware` with a pure ASGI implementation to prevent anyio TaskGroup task-loop mismatch errors in tests using `ASGITransport`
- `tests/conftest.py`: `reset_singletons` autouse fixture clears `get_engine`/`get_sessionmaker` lru_cache and `_pool` between tests; disposes engine on teardown to close asyncpg connections cleanly before each test's event loop closes
- `tests/test_worker.py` `_fake_summarize`: added `**_kwargs` to absorb `project_id`, `client`, `http_client` added in E4-S3
**Smoke test:** DEFERRED — requires E8-S1/S5 human prerequisites on Railway DEV (bot token set, `TELEGRAM_BOT_USERNAME` set, `WEB_URL` set); then: link Telegram from /settings, start a run, confirm bot DM arrives with item count + deep link
**Promoted to backlog:** none

## [E8-S1] Telegram Login + [E8-S5] Telegram Mini App shell
**Completed:** 2026-07-19
**Handover:**
- `backend/src/auth/telegram.py`: `verify_login_widget()`, `verify_webapp_init_data()`, `find_or_create_telegram_user()` — all hash-check logic for Login Widget + Mini App initData
- `POST /auth/telegram/login` (Login Widget), `POST /auth/telegram/webapp` (initData), `POST /auth/telegram/link` (link TG to email account — settings UI in E8-S2), `GET /auth/telegram/config`
- `backend/src/api/telegram_webhook.py`: `POST /telegram/webhook` + `setup_webhook_and_menu()` (called at FastAPI startup via lifespan; self-discovers API URL from `RAILWAY_PUBLIC_DOMAIN`)
- DB: `users.telegram_id` BigInteger unique nullable — migration `f1a2b3c4d5e6`
- `frontend/lib/telegram-webapp.ts`: `isTelegramContext()`, `getTelegramInitData()`, `initTelegramWebApp()`
- `frontend/lib/auth-context.tsx`: `isTelegram` in context; auto-auth via initData on mount when no stored JWT
- Login page: returns `null` inside Telegram; shows Telegram Login Widget when `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME` set
- App layout: logout button + email hidden when `isTelegram`
- ENV vars added (api): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`, `WEB_URL`
- 8 unit tests (`test_telegram_auth.py`); 5 DB integration tests (`test_telegram_webapp.py`)
**Smoke test:** DEFERRED — requires human to: (1) create bot via @BotFather; (2) set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`, `WEB_URL` on Railway DEV api; (3) open bot from phone — Mini App must open authenticated, full flow must work
**Promoted to backlog:** none

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
