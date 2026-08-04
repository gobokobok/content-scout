# DONE — content-scout

Completed stories land here, newest first. Format:

## [E8-S7] Surface token purchases in the Balance ledger
**Completed:** 2026-08-04
**Handover:**
- Extended `GET /me/runs` (no new endpoint) with `kind="purchase"` rows sourced from `TokenPurchase`, appended to the existing runs/deep-analyses list and re-sorted chronologically together — closes the AC's "all filter interleaves" requirement for free, no separate merge logic.
- `project_id`/`project_name` widened to `Optional` (purchases aren't tied to a project); confirmed first that neither is actually rendered anywhere in the current frontend, so this was a safe widening.
- `tokens_charged` doubles as "tokens credited" for purchase rows (positive, same field, opposite meaning) — disambiguated entirely via `kind` on the frontend: "+"/`text-success` for purchases vs. the existing "−"/`text-ink` for spend. `spentThisPeriod`'s total now explicitly excludes purchase rows so a top-up doesn't inflate the "spent" figure.
- `RunDetailSheet` gained a purchase-aware simplified layout (type/date/credited amount only) — optional per the AC, added anyway since it was cheap.
- New backend test helper `make_token_purchase`; 3 new tests. Full suite 371 passed (up from 368). ruff/ruff format/mypy clean; frontend `tsc --noEmit`/`next lint`/`next build` clean. No new dependencies, no ENV vars, no migration.
**Smoke test:** DEFERRED — per CLAUDE.md's no-agent-UI-testing constraint. Needs a real DEV Telegram Stars purchase to confirm the row appears in the «Пополнения» filter with the right amount/date and correct positive styling.
**Promoted to backlog:**
- (none)

## [E20-S1] Batch deep-analysis comment scraping
**Completed:** 2026-08-04
**Handover:**
- Targeted the real bottleneck a real DEV investigation earlier this sprint measured directly: `deep_analysis_extraction.py`'s comment-fetch loop called the `apidojo` actor once per post, sequentially — ~87% of one real run's 12-minute wall time. Replaced with one batched Apify call per DB batch (`summary_concurrency`-sized, default 5), via new `comment_scraper.py:fetch_comments_batch` (module-level, mirrors `fetch_comments`) and `ApifyCommentsClient.fetch_comments_batch`/`_fetch_batch_once` (client-level).
- **Verified live** (WebFetch against the actor's public input-schema page) that `maxItems` is a whole-run cap, not per-post — batched calls request `maxItems = len(posts) × per_post_limit`, then the existing `_sort_and_cap` (D36) enforces the real per-post cap after grouping results back to their source post.
- **The comment→source-post grouping field name could not be independently verified** (no live Apify account access; two web lookups gave inconsistent/likely-hallucinated answers, one contradicting this codebase's own already-working field mapping). Handled defensively: `_match_post_url` tries several plausible field names; an all-unmatched batch response aborts the whole batch back to the original safe per-item path (Apify retry, then Bright Data) rather than risk silently misattributed comments. **Needs a real DEV run to confirm/correct** — flagged prominently in BACKLOG.md's Handover with what to check in `railway logs`.
- Also folded in D41's real bug fix (`resultsLimit` → `maxItems`, the actual field name — the old one was silently ignored, so the per-post comment cap has likely never been enforced) on **both** the pre-existing single-post path and the new batched one, plus the `deep_analysis_comments_per_post` default drop 25 → 15 (matches apidojo's free-included tier, zero overage by default).
- Cost accounting unchanged: still one `UsageEvent` per post, not per batch — batching is a latency change only.
- 12 new/updated backend tests; full suite 368 passed (up from 362). ruff/ruff format/mypy clean. No new dependencies, no ENV vars, no migration.
**Smoke test:** DEFERRED — needs a real DEV deep analysis with 20+ items to (1) confirm wall time actually drops, (2) confirm the grouping-field guess landed correctly (check `railway logs` for the "items could not be matched" warning — should be 0/absent), and (3) confirm the `maxItems` fix actually caps comments at 15 with zero overage `UsageEvent` rows.
**Promoted to backlog:**
- (none)

## [E22-S1] Review Telegram completion message: condensed formatting + quantified summary
**Completed:** 2026-08-04
**Handover:**
- User-supplied exact target format for the Review completion DM, replacing the old inline `·`-joined line and bare-paragraph sections: bulleted account/publication counts, bold `<b>Резюме</b>`/`<b>Топ публикации по виральности</b>` headers, no `•` prefix on top-item lines, a new "Потрачено токенов: N" line, and a header disambiguated against Analysis ("Задача «Ревью»" instead of the old, ambiguous "Анализ завершён!").
- **Real bug found via the AC's own "verify, don't assume" instruction**: `run.progress_items` (total scraped count) is not what the run actually charged — it's never adjusted down when a mid-run token-balance exhaustion truncates `_finish_run`'s summarization batches. Used `run.progress_summarized` (the real per-batch-debited counter) instead; new regression test proves the two diverge.
- `run_summary.py`'s prompt extended with a ТЕГИ block (publication index → topic 1-5) so per-topic counts are aggregated server-side from real tags, not trusted from model arithmetic — topics gain a `"(N)"` suffix when parseable, plain strings otherwise (fully backward compatible, all pre-existing `parse_summary_response` tests unchanged). A deterministic per-`ContentType` fact line ("Форматы: Reels: 25, Карусель: 32…") is now handed to the model before it writes the Резюме, so format claims cite real counts instead of estimating. Fixed a latent regex bug the new ТЕГИ block would have triggered (`_TOPICS_RE`'s old greedy match would've swallowed it as bogus topics).
- Confirmed no frontend change needed — `runs/[runId]/page.tsx` already renders `summary_text`/`summary_topics` as-is, so the richer count-suffixed topic strings show up automatically.
- `docs/PROMPTS.md`'s "Run summary" section updated to match the new prompt/protocol.
- 8 new/extended backend tests; full suite 362 passed (up from 354). ruff/ruff format/mypy clean. No frontend changes, no new dependencies, no ENV vars, no migration.
**Smoke test:** DEFERRED — per CLAUDE.md's no-agent-UI-testing constraint (this is a backend/Telegram-content story with no local way to trigger a real Telegram DM). Needs a real DEV Review run against a mixed content-type spread to confirm the DM renders correctly in Telegram's HTML `parse_mode` and that the summary's cited counts match reality.
**Promoted to backlog:**
- (none)

## [E18-S6] Notification drawer: show task type/time/status instead of stale project name
**Completed:** 2026-08-04
**Handover:**
- Pure frontend render fix, `frontend/app/(app)/layout.tsx` — `tracked.run` (from `useRunTracker`) already carried `run_type`/`created_at`/`started_at`, so no hook or backend change was needed.
- Tracked-run drawer row now reads `{Ревью|Анализ} · {дата и время}` instead of the stale repeated `tracked.projectName` — reuses `RunFeed.runTypeStat`/`runTypeDeep`, the same keys the home feed already uses.
- Schedule-alert row: checked first (per the story's own AC) whether schedules still need project framing post-D38 — they don't, neither the Scheduled Runs page nor the home feed's schedule cards show `project_name` anymore. Replaced the stale project-name title with the skip-reason message itself (previously the second line) and moved `skipped_at` into the second line.
- No backend changes, no new dependencies, no ENV vars, no migration. `tsc --noEmit`/`next lint`/`next build` all clean; no test suite exists for this presentational component (CONVENTIONS.md's frontend bar).
**Smoke test:** DEFERRED — per CLAUDE.md's no-agent-UI-testing constraint. Needs a real DEV/Mini App pass: trigger a Review and an Analysis run, open the bell, confirm both are distinguishable by type/time/status.
**Promoted to backlog:**
- (none)

## [E15-S5] Run results: settings + competitor drill-down modal (Review and Analysis)
**Completed:** 2026-08-04
**Handover:**
- Broadened scope (2026-08-04 PBR, bumped to high priority) of a story originally opened 2026-08-03 from E21-S1's scoping session — see BACKLOG.md's `[E15-S5]` Goal for the concrete DEV-log-diving incident that prompted the broadening.
- Backend AC confirmed both pieces of the sheet's data were already derivable, no schema change: scope was already on `RunOut`; only the account list needed a new endpoint. New `GET /runs/{run_id}/accounts` (`backend/src/api/runs.py`, `RunAccountOut`) — for explicit `account_ids` runs, exactly those accounts; for whole-list runs, every currently-non-archived account in the project's IG list. `succeeded` = has at least one `ContentItem` row for this `run_id`; `fail_reason` mirrors `Account.fail_reason` (the account's own last-attempt reason — the closest signal this project has to a run-scoped one) when not succeeded. Empty list for post-mode Analysis runs (no competitor scope). One endpoint serves both Review and Analysis pages, since the Analysis report page already resolves its underlying `RunResponse` via `analysis.run_id`.
- Frontend: new shared `frontend/components/run-settings-sheet.tsx` (`RunSettingsSheet`) — a settings-gear icon on both `runs/[runId]/page.tsx`'s and `deep-analyses/[analysisId]/page.tsx`'s summary card opens a read-only `BottomSheet` showing scope ("N дней" / "последние N публикаций" / "Одна публикация") plus the scrollable account list with a succeeded/failed indicator per account. New `RunSettingsSheet` i18n namespace.
- New backend tests cover succeeded/failed marking, explicit `account_ids` scoping, post-mode empty list, and cross-user 404 isolation. Full suite 354 passed (up from 350). ruff/ruff format/mypy clean; frontend `tsc --noEmit`/`next lint`/`next build` clean. No new dependencies, no ENV vars, no migration.
**Smoke test:** DEFERRED — per CLAUDE.md's no-agent-UI-testing constraint; verified via new backend tests + typecheck/lint/build. Needs a real DEV pass with a run that has a mix of succeeded/failed competitors (not reproducible without a live Apify failure) to confirm the failed-indicator path, plus a general 375px pass on both pages.
**Promoted to backlog:**
- (none)

## [E3-S8] Run-creation estimate: explain methodology + when balance is deducted (Review)
**Completed:** 2026-08-04
**Handover:**
- Real component is `frontend/components/run-dialog.tsx` — the story's guessed path (`app/(app)/projects/[id]/run-dialog.tsx`) turned out to be dead/orphaned code from before E18's redesign consolidated the dialog into `components/`, confirmed via a repo-wide import search before touching anything.
- New RU string `reviewEstimateExplanation` (`RunDialog` namespace, `frontend/messages/ru.json`), rendered beneath the cost-estimate block for the Review path (`!isDeepAnalysis`), mirroring the existing `deepEstimateExplanation` (Analysis path, shipped by `[E21-S2]`).
- Copy was corrected against real behavior before finalizing, per the AC's explicit requirement: `worker.py`'s `_finish_run` debits `token_balance` incrementally — 1 token per publication, per batch, during the `summarizing` phase — not as a single "after completion" event as the story's draft copy assumed. Final copy: "Оценка — по количеству отобранных публикаций (1 токен за публикацию). Токены списываются по ходу выполнения запуска, а не при подтверждении." Worth noting for any future billing-transparency story (e.g. `[E15-S5]`): Review's charging is already the same incremental shape as Analysis's D50 model, not a lump sum.
- No backend changes, no tests (pure copy change — CONVENTIONS.md's frontend test bar is typecheck + eslint), no ENV vars, no new dependencies.
**Smoke test:** DEFERRED — per CLAUDE.md's no-agent-UI-testing constraint (no Browser tool/scratch-preview for frontend changes this session); verified via `tsc --noEmit` + `eslint` (both clean) and direct code reading of the real debit path. Needs a real DEV pass at 375px to confirm the two-line block (estimate + explanation) reads cleanly.
**Promoted to backlog:**
- (none)

## [E21-S2] Standalone Analysis pipeline: own scraping, single-account/post scope, incremental token charging
**Completed:** 2026-08-04
**Handover:**
- Implemented per D50 (architecture) and D49 (entry-flow scope), by direct user request to deliver the full story in one session with no intermediate check-ins. Analysis (`run_type="deep_analysis"`) no longer chains off a finished Review run — it does its own scrape, in one of two modes: pick exactly one account + a days/count scope (same UI pattern Review already uses), or paste a single publication URL (no scope step, analyzes only that post).
- Backend: new migration adding `analysis_mode`/`target_post_url`/`comments_limit` to `analysis_runs`/`scheduled_runs`; `InstagramPlatform.fetch_post(url)` for single-post lookup, auto-resolving/creating the author as a real `Account` so every existing account-joined query (virality, exports, Telegram notify) keeps working unmodified; `worker.py` rewritten so `run_analysis` runs scrape→extract→synthesize as one continuous job for deep_analysis runs (no more separate auto-chain enqueue); token charging is now incremental (`1 + comments_analyzed_count` per item, charged as each one completes, balance-checked per batch) instead of an up-front lump sum with post-hoc refund/reconciliation.
- Frontend: `deep-analysis-sheet.tsx` (dead run-picker UI from the old auto-chain flow) deleted; `run-dialog.tsx`/`scheduled-run-dialog.tsx` extended with the two entry modes, a token-based cost estimate, and (after smoke-test feedback) a dedicated mode-picker screen + account-before-scope step order.
- **Three real bugs found via the user's own DEV smoke test, none caught by the 350-test suite** (see BACKLOG.md's `[E21-S2]` Changelog for the full blow-by-blow): (1) Sonnet reliably omitted the required `stats` object when synthesizing a report from a single publication with zero comments — fixed with an explicit prompt instruction; (2) `/me/usage` showed a phantom second "Review" line for every Analysis, since it unioned `AnalysisRun` rows without excluding `run_type="deep_analysis"` — post-D50 that row isn't a separate billable event anymore; (3) `deep_analysis_extraction.py` charged for every comment *fetched* but only ever fed the first 25 into the actual analysis prompt (a stale constant from before `comments_limit` was configurable) — a real overcharge above 25 comments, fixed by removing the redundant cap.
- **Real external limitation found, not a code bug:** the Apify account is on a Free Plan for `apidojo/instagram-comments-scraper-api`, which silently caps real comment output at 10/post regardless of the requested limit, and still reports `SUCCEEDED` so the BrightData fallback never triggers (which isn't configured on DEV anyway). The `comments_limit` ceiling was still raised 50→100 and 50/100 option chips added per direct request, but 15/25/50/100 are shipped as disabled/greyed-out teaser chips (only 5/10 are live) until `[E20-S5]` (new, below) resolves the underlying account limitation.
- 350 backend tests (up from 349 pre-story), ruff/mypy/tsc/eslint/`next build` clean throughout all four rounds of work. Five commits total, all pushed same day, CI green, DEV health-checked after every deploy.
**Smoke test:** PASSED — user-executed on DEV across two initial rounds (account mode, then post mode after the synthesis fix) plus a comments-limit/UX follow-up round; all explicitly confirmed working. The final polish round (teaser chips, mode-picker styling) was deployed after those confirmations and not separately re-verified by the user.
**Promoted to backlog:**
- `[E20-S5]`: resolve the Apify Free Plan comment-count ceiling (upgrade the plan, or configure a working BrightData fallback) — blocks re-enabling the disabled 15/25/50/100 comments_limit options

## [E17-S11] Deep-analysis pipeline hardening: synthesis truncation, logging visibility, timeout headroom, notification timing, usage-based charging (D48)
**Completed:** 2026-08-04
**Handover:**
- Backfilled at the 2026-08-04 `/sprint-review`, same pattern as `[E2-S4]`/`[E8-S8]`/`[E17-S10]` — three real bugs found live via `railway logs` diagnosis across two DEV Analysis run investigations (2026-08-03, 2026-08-04), fixed same-session each time, no story ID until now. Full per-session detail lives in SPRINT.md's three "Untracked fix" narrative blocks and BACKLOG.md's `[E17-S11]` entry (AC/DoD); summarized here.
- **Synthesis truncation** (`df61614`): Sonnet's `max_tokens` was hardcoded at 4096 in `deep_analysis_synthesis.py` — too small for `REPORT_TOOL`'s multi-array Russian-language schema at real item counts, silently truncating the `tool_use` block with no exception raised. Now `Settings.deep_analysis_synthesis_max_tokens` (default 8192); both silent fail-branches now `logger.warning` with `stop_reason`.
- **Root logger never configured**, found while chasing why the above produced zero log output anywhere: neither `main.py` nor `worker.py` called `logging.basicConfig`, so arq's and uvicorn's own-namespace-only logging configs meant every `logger.*` call project-wide was going nowhere in Railway. Fixed in both entrypoints — systemic, not incident-specific.
- **Timeout headroom + diagnostics** (`1ae1205`): `apify_content_scrape_timeout_secs` 180s→240s after a real account's retry landed within 14s of the old timeout; added `logger.info`/`logger.warning` for run scope (account count/`duration_days`/`item_limit`), Apify retry attempts, and the 50-item scrape-ceiling case.
- **Notification timing + D48 token-charging redesign** (`f683a3c`): `notify_run_complete` was firing a "done" DM for `deep_analysis` runs right after the base scrape finished, 12 minutes before the real Analysis result existed — split into a deep-analysis-aware skip, a new `notify_deep_analysis_complete` (fires on real completion, success or failure), and a `_notify_base_scrape_only` fallback so every run still gets exactly one DM. **D48**: token charging moved from a flat 15-tokens/item estimate to 1 token/publication + 1/comment actually analyzed, reconciled post-hoc against real `DeepAnalysisItem` counts (`_reconcile_real_usage`) — two real runs showed Apify's Free Plan silently capping comments at 10/post regardless of the configured 25 target, so the flat charge was billing for coverage never delivered. `deep_analysis_thin_coverage_multiplier` (E17-S9) removed as redundant under usage-based billing.
- New test `test_synthesize_report_truncated_response_marks_failed_and_logs_stop_reason`. Full suite 339 passed, `ruff`/`ruff format --check`/`mypy src` clean throughout. Deployed to DEV across all three pushes, CI green each time.
**Smoke test:** PASSED (partial) — synthesis-truncation and timeout fixes each confirmed by the very next real DEV run succeeding/landing with margin. Notification-timing correctness and D48's reconciled charge amount on a real run not yet independently re-verified — folded into `[E19-S3]`.
**Promoted to backlog:** none new — `[E19-S3]` (new, this session) already covers the two open verification items above alongside Sprint 11's other deferred smoke tests.

## [E20-S3] Baseline rate limiting & provider-quota guardrails
**Completed:** 2026-08-03
**Handover:**
- Picked up right after `[E20-S2]` per Sprint 11's declared order, now buildable against a real, memory-pin-confirmed 25-concurrent-Apify-run ceiling (D44/D46).
- New `services/apify_governor.py`: `acquire_apify_slot(limit)`, a Redis sorted-set-backed global semaphore (atomic Lua check-and-add, so a naive two-round-trip check-then-add can't let concurrent acquirers all pass and overshoot the limit) with stale-entry pruning so a crashed worker's un-released slot doesn't permanently shrink capacity. Wraps all three real Apify actor call sites: `platforms/instagram.py`'s `_fetch_once`/`_fetch_profile_once`, `comment_scraper.py`'s `ApifyCommentsClient._fetch_once`. New `Settings.apify_max_concurrent_actor_runs` (default 25, D44).
- `middleware/rate_limit.py`'s `check_rate_limit()` gained an optional `key` param, bucketing by that key instead of caller IP when given — used to key run-creation/deep-analysis-creation limiting by user id, since IP-based limiting is a poor fit for authenticated write endpoints behind shared/mobile NATs (and would have collided across this project's own test suite, which shares one fake IP). `POST /projects/{id}/runs` and `POST .../deep-analyses` each gained a short-window per-user limiter, `Settings.write_endpoint_rate_limit_per_minute` (default 5/min) — distinct from E7-S4's existing daily quota.
- Scheduled-run burst AC closed with no new code: `fire_due_schedules` already enqueues through the same path a manual run uses, so a burst of schedules firing in one 5-minute cron tick is already bounded by the governor plus `WorkerSettings.max_jobs=5` (D46) — the story's AC explicitly allowed "governor absorbs it, or stagger," and the governor already does.
- New **D47**, superseding D11 for these specific mechanisms.
- Tests: new `tests/test_apify_governor.py` (governor concurrency/exception-release/limit behavior, via a small in-memory fake mirroring the real Lua script). `tests/test_guardrails.py` gained a `key`-bucketing unit test plus endpoint-level 429 tests for both new call sites. `test_instagram_platform.py`/`test_comment_scraper.py`'s hand-built test doubles needed a `_max_concurrent_actor_runs` attribute added (same pattern as E20-S2's `_memory_mbytes`). Full suite: 331 passed (up from 325). `ruff`/`ruff format --check`/`mypy src` all clean.
- This session's sandbox has a working local Redis (`redis-cli ping` → `PONG`), same discovery as the earlier "local Postgres available" finding — the new tests exercise it directly (real Redis, not just mocks) rather than deferring that verification, since per-user-id bucketing means fresh test users never collide across the suite.
**Smoke test:** DEFERRED — pushed and deployed to DEV (commit `968e986`, CI green, `/health` confirmed), but observing the governor under real concurrent load still needs either a live Apify console pull during real concurrent DEV runs or several genuinely concurrent triggered runs, same established pattern as every other Apify-account-dependent verification in this project.
**Promoted to backlog:** none.

## [E20-S2] Worker & DB capacity for concurrent load
**Completed:** 2026-08-03
**Handover:**
- Picked up ahead of `[E20-S3]` (Sprint 11's declared next item) after that story's own dependency check flagged its 25-run governor shouldn't be built until this story's Apify memory pin landed — direct user confirmation to do E20-S2 first when asked.
- `Settings.apify_actor_memory_mbytes` (default 256, D44) now pinned on every `ActorClientAsync.call()` in `platforms/instagram.py` (`_fetch_once`, `_fetch_profile_once`) and `comment_scraper.py`'s `ApifyCommentsClient._fetch_once` — replaces Apify's non-deterministic per-run RAM default (observed swinging 128–4096 MB on identical workloads).
- `Settings.worker_max_jobs` (default 5) now sets `WorkerSettings.max_jobs` explicitly in `worker.py` — sized so the worst case (every concurrent worker job is a `run_analysis` job × `scrape_concurrency`=5 Apify calls each) lands exactly at the confirmed 25-concurrent-Apify-run ceiling, fixing the previous unset-default overshoot (10 × 5 = 50, already 2× over).
- `Settings.db_pool_size`/`db_max_overflow` (10/10) now flow into `get_engine()`'s `create_async_engine()` call, replacing SQLAlchemy's unconfigured default (5+10=15). Fetching `DATABASE_URL` to check the real `max_connections` was correctly blocked as credential access this session; the user confirmed it directly via the Railway dashboard's Postgres query tab shortly after close: **DEV `max_connections=100`**, comfortably above the 40-connection worst case (20/process × api + worker) — the chosen pool values are confirmed safe as-is.
- New **D46**: records the four config changes above plus the decision that `api`/`worker` stay at `numReplicas: 1` for now, with explicit revisit thresholds (sustained arq queue depth across cron ticks, or p95 API latency > 500ms) — neither measured yet.
- New env vars (ENV.md): `WORKER_MAX_JOBS`, `APIFY_ACTOR_MEMORY_MBYTES`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` — all optional, defaults match the values above.
- Tests: `test_instagram_platform.py`/`test_comment_scraper.py`'s fake Apify actor clients now require and assert `memory_mbytes=256`; new `test_worker.py::test_worker_max_jobs_stays_within_apify_concurrency_ceiling` asserts the `max_jobs × scrape_concurrency ≤ 25` invariant directly; new `test_db.py` asserts `get_engine()` passes the configured pool kwargs to `create_async_engine` (mocked, no real DB connection needed). Full suite: 325 passed (up from 281 at Sprint 9's close). `ruff check`/`ruff format --check`/`mypy src` all clean.
**Smoke test:** PASSED — confirmed live on DEV via `[E19-S3]` (2026-08-04): the `Memory: 256 MB` pin lands on real Apify run-detail pages, and enqueueing more than 5 concurrent runs shows the expected queueing behavior at `max_jobs=5`. (Postgres `max_connections` confirmed separately, same day as original close, at 100 — see Handover above.)
**Promoted to backlog:** none — unblocks `[E20-S3]`, next in Sprint 11's declared order.

## [E21-S1] Scope standalone Analysis pipeline: Apify usage audit + worker capacity
**Completed:** 2026-08-03
**Handover:**
- Scoping-only story (D40) — no code shipped, this closes the discussion/audit, not an implementation. Full write-up lives in BACKLOG.md's `[E21-S1]` Handover; summarized here.
- **Apify usage audited**: base Review scrape (`InstagramPlatform`, `apify/instagram-scraper`, $0.0027/item) is unaffected by any of this. Comment scraping (`comment_scraper.py`, Analysis-only) was verified **live against Apify's actual Store pages**, not assumed: the primary vendor (`apidojo/instagram-comments-scraper-api`) accepts only direct post URLs (no profile/username input, no post-discovery), has no comment-sort/order parameter at all, and — the real finding — our code sends it a `resultsLimit` field that doesn't exist in the actor's schema (`maxItems` is the real one), meaning the per-post comment cap has likely never been server-side enforced. Logged as **D41**; fix + a cap reduction (25→15 comments/post, to stay inside the vendor's free included tier) folded into the already-open `[E20-S1]` rather than opened as a new story, since it's the same call site.
- **Standalone-Analysis proposal, user sign-off (D42)**: Analysis gets its own account-selection + scrape (own `InstagramPlatform` post-discovery + own comment fetch, no more reading a Review run's `content_items`), capped at 20 competitors per Analysis run (independent of the account list's existing 50-cap, D13 — more competitors means multiple parallel Analysis runs), with incremental per-item token charging replacing today's up-front lump-sum charge (`start_deep_analysis`) so a mid-run failure only burns tokens for completed work.
- **New general policy (D43)**, surfaced from the same conversation and broader than Analysis: any run (Review or Analysis) that stops mid-way must still show whatever results were produced before the stop, with a disclaimer, and bill only for work done. Checking this against the actual Review frontend surfaced two live gaps: `runs/[runId]/page.tsx` gates its tabs entirely on `run.status === "done"` (a `failed` run with already-committed partial data shows nothing), and `run.error_message` — already returned by the API and typed on the frontend — is never rendered anywhere on that page, unlike the deep-analysis report page which already shows its equivalent field.
- **Follow-on stories opened**: `[E21-S2]` (the actual standalone-pipeline implementation — own scrape, 20-cap, incremental charging), `[E21-S3]` (Analysis publications tab, depends on E21-S2), `[E15-S4]` (Review run-detail partial-results + disclaimer display, D43), `[E15-S5]` (Review results competitor drill-down modal — a separate direct feature request surfaced in the same conversation, no dependency on E21). `[E20-S1]`'s scope grew (D41) but wasn't split into a new story.
- 200-DAU worker/provider capacity math was **not** produced — Apify/Anthropic account-level concurrency and RPM/TPM limits are dashboard-only facts this session couldn't check, same blocker `[E20-S3]` already had; still open there, not resolved by this story. AI-insights UX review was raised and explicitly deferred by the user for a separate discussion — no story opened.
**Smoke test:** N/A — scoping/discussion story, no code change.
**Promoted to backlog:** `[E21-S2]`, `[E21-S3]`, `[E15-S4]`, `[E15-S5]` (all new); `[E20-S1]` expanded in place

## [E2-S4] Competitor deletion, picker staleness, and picker scroll fixes
**Completed:** 2026-08-02
**Handover:**
- Direct user bug reports in chat, untracked at the time — backfilled as a story per this project's story-tracking discipline before closing. Three real, separate bugs, found and fixed one at a time as each fix's live retest surfaced the next:
  1. **Deletion failed on any competitor with scrape history** — `content_items.account_id` (and transitively `shortlist_items`/`deep_analysis_items`) has no `ON DELETE` cascade, so deleting such an account hit an unhandled `IntegrityError` → 500 → the frontend's generic error toast. Fixed by making deletion a soft-delete: new `Account.archived_at` (migration `a2b3c4d5e6f7`, mirrors `Project.archived_at`), `DELETE` sets it instead of removing the row, `GET` filters it out, `POST` un-archives a matching `normalized_url` in place (same id, history intact) instead of erroring on the unique constraint. The DB-level 50-per-list cap trigger (D13 backstop) is rescoped in the same migration to count only non-archived rows.
  2. **Run-creation competitor picker showed a stale list** — `accounts` was fetched once on page mount in both `app/(app)/page.tsx` and the per-project `results/page.tsx`, never refreshed on dialog open. Fixed by refetching and awaiting the fresh list *before* mounting `RunDialog`, since it only seeds its local selection from that prop once per mount (deliberately, to not clobber in-progress user edits).
  3. **Competitor picker list didn't scroll** — the real bug, and the hardest to isolate (see BACKLOG.md's `[E2-S4]` Changelog for the full DevTools-driven diagnosis trail). Root cause: the scroll container is itself `display:flex;flex-direction:column`, and its middle child (the rounded-border box wrapping competitor rows) has `overflow-hidden` with no explicit `min-height` — per the flexbox spec this gives it an automatic minimum size of 0, so the browser crushed it via flex-shrink to fit the fixed-height container, clipping rows through its own `overflow-hidden`, instead of ever letting the outer container overflow and scroll. Fixed with `shrink-0` on that inner box (`run-dialog.tsx`, `scheduled-run-dialog.tsx`). Two earlier, real fixes for other scroll failure modes (`min-h-0 flex-1` on the outer scroll containers; `Telegram.WebApp.disableVerticalSwipes()`) remain in place as genuine hardening, just weren't what fixed this specific bug.
  4. **Deploy-pipeline gotcha, not a code bug:** after the real fix shipped, DEV kept serving a stale bundle across multiple green-CI redeploys — a stuck Railway/BuildKit build cache reusing an identical container image digest regardless of source changes. Worked around by bumping an env var on the DEV `web` service (Railway's cache busts on env var changes) and redeploying manually with `railway up frontend --path-as-root --service web`, which also hit the same "`railway up` from a subdirectory uploads the whole monorepo root" gotcha `[E17-S10]` documented for `backend`/`worker` — now confirmed to apply to `web` too.
- New codebase-wide CSS lesson: a flex item with non-`visible` overflow and no explicit `min-height`, nested inside another height-constrained flex container, is eligible to be crushed by flex-shrink instead of the intended ancestor ever scrolling. `shrink-0` it if it should never compress.
- 3 new/rewritten backend tests in `test_accounts.py` (archive-preserves-history, re-add reactivates, archived rows don't count against the cap trigger); full suite 323 passed, ruff/mypy/tsc/eslint clean.
- ENV vars added: none permanent (a temporary `BUILD_CACHE_BUST` var was set and removed on the DEV `web` service, purely to bust the stuck build cache).
**Smoke test:** PASSED — user's own live retest on DEV, both web and Telegram Mini App: deletion of a competitor with run history succeeds, re-adding it reactivates the same account, and the run-creation picker's competitor list (9+ items) now scrolls correctly.
**Promoted to backlog:** none new — the Railway build-cache/`--path-as-root` gotcha was folded into this story's and `[E17-S10]`'s handovers as a documented pitfall rather than a new story, since there's no code fix to schedule, only a runbook note.

## [E19-S1] DEV smoke-test sweep (trimmed)
**Completed:** 2026-07-31
**Handover:**
- Closed the ~13-item DEV smoke-test gap carried over from Sprint 10, mandatory-first for two sprints running. User ran the live sweep on real DEV/PROD; this session cross-checked several items against the existing backend test suite before touching any DONE.md line, which closed 4 of the 12 AC items with **no live re-test needed** since they were already asserted on every CI run: cross-user 404 isolation (`test_create_deep_analysis_404_for_foreign_run`/`test_get_deep_analysis_404_for_missing_or_foreign`), forced-malformed-synthesis→`failed` (`test_synthesize_report_malformed_tool_input_marks_failed`/`test_synthesize_report_missing_tool_use_marks_failed`), rate-limit/quota 429s + XLSX formula-injection guard (`test_rate_limit_blocks_after_threshold`/`test_run_quota_blocks_on_limit`/`test_safe_text_prefixes_formula_triggers`), and duplicate-insert-is-noop on re-enqueue (`test_process_run_duplicate_insert_is_noop`).
- 6 items confirmed live by the user: the Apify `apidojo` vendor gap is resolved, thin-comment-coverage token reduction, insufficient-balance rejection + auto-chain skip-reason/failure cards, scheduled-run cron firing + Telegram DM, the PROD completion-DM link, and a direct-DB `scheduled_runs` schema check + `is_admin=true` unlocking `/admin`.
- 1 item explicitly deprioritized by direct user choice without live verification: the zero-balance-schedule skip-badge-within-one-cron-tick edge case.
- **Real finding #1 — stale AC, not a bug:** the "register-without-invite-code fails" check turned out to assert behavior that stopped being true on 2026-07-19 (commit `053cbe3`, "open registration with 50-token starting balance") — it superseded E7-S4's invite-code guardrail the same day it shipped, but that removal was never logged as a decision. `git log -S registration_invite_code` confirmed zero enforcement call sites remain anywhere in `backend/src/`. Backfilled as **D39**; corrected E7-S4's DONE.md handover (struck the now-false invite-code bullet); replaced the AC's originally-planned test with `test_register_succeeds_without_invite_code` in `backend/tests/test_auth.py`, asserting the actual current behavior (open registration, `token_balance=50`) instead of the stale one.
- **CI broke on push, fixed same session:** the new test added one more `/auth/register` call to `test_auth.py`, which tipped the file over `middleware/rate_limit.py`'s shared 10-per-minute-per-path counter — a real (not local-only) test-isolation gap, since CI's Redis persists across the whole file/session with no reset between tests, and this file's tests were never meant to exercise rate-limiting (`test_guardrails.py` owns that specifically). CI failed clean on `tests/test_auth.py::test_update_display_name_rejects_too_long` (`KeyError: 'access_token'`, i.e. a silent 429). Fixed with an autouse `_bypass_rate_limit` fixture patching `src.api.auth.check_rate_limit` to a no-op for the whole file, matching the `_noop_rate_limit` pattern already established in `test_guardrails.py`. Confirmed stable across 3 repeat local runs (16/16 passing each time) and the full 320-test suite passing after the fix. The separately-documented local-Postgres test-order flake (8 failures when this file was run standalone against this sandbox's possibly-dirty local Postgres, first noted in `[E14-S6 follow-up 2]`'s handover) is a different, pre-existing issue, confirmed unrelated via `git stash` before this fix.
- **Real finding #2 — Telegram DM opens the browser, not the Mini App:** `telegram_notify.py:notify_run_complete` sends a plain HTML `<a href>` anchor; Telegram opens that in the system browser rather than inside the Mini App (unlike the chat menu button, which already uses a `web_app`-type config). Opened new story **[E8-S9]** rather than fixing ad hoc — needs the Bot API's inline-keyboard `web_app` button instead, plus a check on whether that requires a BotFather-registered short name.
- **Real finding #3 — product-direction change, bigger than this story:** the user's response to the cross-run-summary-reuse check turned into "Review and Analysis are two separate runs, we no longer trigger analysis from review, analysis is standalone" — confirmed scope is the full independent-pipeline version (Analysis gets its own Apify scraping, not just a detached trigger). Logged as **D40**; opened new epic **E21 (Standalone Analysis Pipeline)** starting with scoping-only story **[E21-S1]** (Apify usage audit + worker capacity), deliberately left unimplemented pending that discussion — not squeezed into this verification-only story.
- Split the one item the user wants to do later (8+-account wall-time timing, E3-S6) into its own story **[E19-S2]** so this story could close without blocking on it.
- Also found and left a specific, non-blocking deferral: E17-S10's real forced-timeout end-to-end test still hasn't been run live (regression-tested only) — noted in its own DONE.md line, not folded into a now-closed story.
**Smoke test:** PASSED — this story *is* the smoke test; 11 of 12 original AC items confirmed one way or another (live, via existing CI, or explicitly closed by user choice), 1 split into [E19-S2].
**Promoted to backlog:** [E8-S9] (Telegram DM Mini App deep link), [E21-S1] (Standalone Analysis Pipeline scoping, new epic E21), [E19-S2] (E3-S6 wall-time timing, split from this story)

## [E17-S10] Deep-analysis job-cancellation bug fix
**Completed:** 2026-07-31
**Handover:**
- Checking a user-reported DEV deep analysis (50-competitor project, "Мой блог") found it stuck in `extracting` for 2.5+ hours with zero `deep_analysis_items` rows created — not a token-balance issue (the requesting user had 7,920 tokens; the base scrape had finished clean).
- Root cause: `process_deep_analysis` (worker.py) caught `Exception` but not `asyncio.CancelledError`, which is a `BaseException` in Python 3.8+. arq's `job_timeout` (3600s) cancels the job task via `asyncio.wait_for`, and that cancellation bypassed the handler entirely, leaving the row permanently stuck instead of transitioning to `failed`. Directly violates E17-S4's own AC ("never leave a row stuck mid-pipeline"). `process_run` already had the correct pattern one function up in the same file — this fix ports it: catch `asyncio.CancelledError` separately, mark `failed` with the same "Превышено время выполнения" message, refund `tokens_charged` via `fail_deep_analysis`, commit under `asyncio.shield` (survives the same cancellation that triggered it), then re-raise.
- New regression test `test_process_deep_analysis_cancellation_marks_failed`, mirroring the existing `test_process_run_cancellation_marks_failed` pattern. Full `test_worker.py` 20/20 passing, ruff/mypy clean.
- The specific orphaned DEV row (`88e50be4…`) was manually corrected via direct DB write (status → `failed`, tokens refunded) since the code fix only prevents future occurrences.
- **Deploy hit real friction**: the GitHub Actions `railway up` deploy step failed 4 times in a row with 3 different transient Railway-side errors (upload 500, auth "Not signed in" ×2, upload timeout) — none of them our code (`backend`/`frontend` CI jobs passed clean every time). Deployed instead via direct local `railway up`, which then surfaced a second, real gotcha: a plain `railway up` from within `backend/` silently uploaded the whole monorepo root instead of just `backend/`, because this machine's Railway project link is rooted at the repo root (`~/.railway/config.json`), not the shell's cwd — nixpacks failed to detect a build plan against the mixed-directory tree. Fixed by using `railway up backend --path-as-root --service api` (and the same for `worker`/`web`), which uploads the given path as the archive root regardless of the local link. Worth remembering for any future manual/local Railway deploy in this monorepo.
- Also surfaced **E20** (Performance & Scale, new backlog epic — see BACKLOG.md) from the same investigation, at direct user request: comment scraping is one-actor-call-per-post rather than batched, every Railway service runs at `numReplicas: 1` with arq's default `max_jobs=10` and an untuned default DB connection pool, and there's no rate limiting beyond D11's original MVP scope. A proposed (unapproved) 50→20 competitor-cap change was scoped separately and explicitly gated on product-decision confirmation, not bundled in as settled.
**Smoke test:** DEFERRED — worker deploy confirmed healthy (`railway logs` clean startup + normal cron ticks, `/health` ok), but a real forced-timeout end-to-end test (an actual arq `job_timeout` cancellation, live) hasn't been run. Surfaced during E19-S1's sweep (2026-07-31) but not addressed there — the fix already has dedicated regression coverage (`test_process_deep_analysis_cancellation_marks_failed`), so this is accepted as a low-priority, not-yet-forced-live gap rather than a blocking one. Pick up only if a real timeout recurs or on a deliberate low-`worker_job_timeout_secs` test.
**Promoted to backlog:** E20-S1..S4 (Performance & Scale epic, drafted this session — see BACKLOG.md), E8-S8 backfilled (see below) from an unrelated but concurrently-discovered untracked-fix cluster.

## [E8-S8] Telegram Mini App: iOS 401 recovery + auto-project creation (D38)
**Completed:** 2026-07-30
**Handover:** direct user bug report, backfilled as a story at the 2026-07-31 `/sprint-review` (see BACKLOG.md's `[E8-S8]` entry for AC/DoD) — was untracked at the time, same as every prior "hotfix"-labeled entry in this file, but self-flagged for backfill below and caught cleanly at the next review.
- User reported the DEV Mini App broken on iOS (Android fine, PROD fine — PROD predates the whole E18 nav overhaul so isn't a useful comparison): Competitors said "Требуется вход в систему" even after auto-login, and the "+" FAB's run-type picker did nothing.
- **Bug 1 — mid-session 401 race, iOS-specific.** Pulled real DEV Railway logs (`railway logs --service api`) and found a working session suddenly getting a burst of 401s across `/projects`/`/me/run-feed`/`/me/scheduled-run-feed`, immediately followed by the app silently re-running Telegram's initData auto-login and recovering on its own — a known class of issue with iOS's Telegram webview being more prone to losing `localStorage` state mid-visit than Android's. Fixed in `frontend/lib/api.ts`: any 401 (outside `/auth/*`) while inside Telegram now silently re-derives a token from initData and retries the request once, before ever surfacing an error to the user. No-op outside Telegram.
- **Bug 2 — no project-creation path for brand-new accounts, not actually iOS-specific.** A second test on a genuinely new device + new Telegram account still failed the same way. Root cause: the E18 nav overhaul (2026-07-26/27) replaced the old project-list home page with the run feed and never carried forward any way to create a project — grepped the whole frontend, zero `createProject` call sites anywhere. Every existing pilot account already had a project from before the redesign, so this was never caught. A fresh account has zero projects, and both the competitors redirect page (nothing to redirect to → hangs on its skeleton forever) and the FAB's run dialog (gated on a default project that stays permanently `null`) silently do nothing.
- **New decision D38**: rather than add project-creation UI back, per direct user feedback ("we do not need a concept of Projects... all runs are done within the account without splitting it into projects") the fix makes one-project-per-user the actual invisible product behavior. `backend/src/auth/providers.py:create_user_with_workspace` now also creates a default project ("Мой блог") in the same transaction as D6's workspace auto-creation — covers both email/password and Telegram signup, since both already funnel through this one helper. `Project` stays exactly as-is in the data model/API; this is a UX simplification, not a schema change.
- Frontend: removed the project-creation prompt UI added earlier in this same session (it's no longer needed — new accounts get a project automatically now); `page.tsx`'s `loadDefaultProject` keeps a silent fallback (`api.createProject` with no visible prompt) only for accounts created before D38 shipped. Deleted the now-fully-orphaned `Projects` i18n namespace from `ru.json` (zero references anywhere after the prompt UI's removal — it had already been dead since the E18 nav overhaul, just newly confirmed).
- 1 new/extended backend test (`test_register_creates_user_and_personal_workspace` now also asserts a project exists); full suite 318 passed, ruff/mypy clean. Frontend `tsc --noEmit`/`next lint`/`next build` all clean.
- Deployed to DEV across three separate pushes as the investigation progressed (`4ac273f` the 401 fix, `b9f2c9f` the first project-creation-prompt attempt, then this D38 change superseding that prompt) — CI green and DEV healthy after each.
**Smoke test:** PASSED — confirmed live on DEV via `[E19-S3]` (2026-08-04): a genuinely new Telegram account/device opening the Mini App has the home feed immediately usable (no prompt), the "+" FAB works right away, and Competitors resolves normally.
**Promoted to backlog:** none new — E8-S7 (surface token purchases in the ledger) is still the only open item from E8-S3.

## [E8-S3] Telegram Stars token top-ups
**Completed:** 2026-07-29
**Handover:**
- Re-scoped mid-story per **D37** (supersedes D30): pay-as-you-go top-ups (quick picks 1000/2000/5000 + custom, minimum 300 tokens, 1 токен = 1 ₽) via a **one-time** Telegram Stars invoice — not the recurring subscription originally planned. User redirected this directly in chat before any code was written.
- `backend/src/services/billing.py`: `create_stars_invoice(user_id, tokens)` (Bot API `createInvoiceLink`, no `subscription_period`), `parse_topup_payload`, `credit_purchase` (idempotent on `telegram_charge_id` — dedupes a retried `successful_payment` webhook). `backend/src/api/billing.py`: `POST /billing/purchase-invoice`.
- `backend/src/api/telegram_webhook.py` now handles `pre_checkout_query` (always accepted) and `message.successful_payment`. Fixed a real bug found while wiring this: `setup_webhook_and_menu`'s `allowed_updates` only listed `"message"`, which would have silently dropped every `pre_checkout_query` update — Telegram doesn't deliver update types that aren't explicitly requested.
- New table `token_purchases` (migration `d4e5f6a7b8c9`), one row per credited charge, unique on `telegram_charge_id`. Verified with a real local-Postgres upgrade/downgrade/upgrade round-trip.
- Frontend: purchase picker (quick chips + custom field) added to `usage/page.tsx`'s buy-tokens button (previously a "coming soon" toast, built speculatively in E18-S5); `lib/telegram-webapp.ts` gained `openInvoice`/`openTelegramInvoice`. The `insufficient_token_balance` run-creation error now links to `/usage` from the shared `components/run-dialog.tsx` (a clickable link, not an auto-redirect, so a failed submit doesn't yank the user out of an in-progress dialog).
- New config: `stars_per_token` (1.0, D37 placeholder pending real FX — Stars can't invoice in RUB directly) and `min_token_purchase` (300). No ENV vars added.
- New DECISIONS.md entry **D37** records the re-scope and flags one unresolved question: Telegram's real per-invoice Stars amount ceiling couldn't be confirmed from docs available this session (no live Bot API access in this sandbox) — `billing.py` surfaces `createInvoiceLink` failures as a clean error rather than assuming a specific cap, but the real limit should be confirmed on the first live DEV smoke test.
- 17 new backend tests; full suite 318 passed (up from 301), ruff/mypy clean. Frontend `tsc --noEmit`/`next lint`/`next build` all clean.
- This story ran **out of the sprint's declared order** — SPRINT.md/CLAUDE.md mark E19-S1 (the mandatory smoke sweep) as "do first" in Sprint 10, but the user explicitly chose to proceed with E8-S3 first when asked. E19-S1 is still outstanding.
- Post-close UI polish (2026-07-29, user feedback): the purchase sheet's price line previously read "К оплате: {amount} ₽" — misleading, since the actual charge is in Telegram Stars, not roubles (₽ only describes D37's *pricing rule*). Now reads "{amount} ⭐" via a lucide `Star` icon (D28 — no emoji) with an explicit "Оплата принимается только в Telegram Stars" note. The custom-amount field's placeholder now mirrors the selected quick-pick amount instead of a fixed 300.
**Smoke test:** DEFERRED — needs a real DEV pass with actual Telegram Stars (test mode): buy tokens via a quick-pick and a custom amount, confirm `token_balance` increases correctly and a previously blocked run unblocks; also the first opportunity to confirm D37's open question about Telegram's real per-invoice Stars ceiling.
**Promoted to backlog:** E8-S7 (surface `token_purchases` rows in the Balance ledger's «Пополнения» filter, which has been an empty state since E18-S5 with nothing real to show until now)

## [E18-S5] Usage page rework around Balance
**Completed:** 2026-07-28
**Handover:**
- **Backfilled at `/sprint-review` time (2026-07-28)** — this story and E18-S1..S4 were implemented 2026-07-26 through 2026-07-28 with no story IDs, no BACKLOG.md entries, and no DONE.md handovers at the time; the sprint review's untracked-fix scan found the whole IA had changed underneath the docs. See BACKLOG.md's `[E18-S5]` entry for full AC/DoD and `git log c2e0861..HEAD` for the source commits (`1c66184`, `c077dd4`, `5d3ba82`, `ab26147`, `500a700`).
- Renamed Usage → Balance/Tokens, folded the standalone header into the black balance card itself, added a buy-tokens CTA stub (links to a payment page that doesn't exist yet — **this is Sprint 10/E8-S3's real entry point**, built speculatively ahead of that story).
- Ledger lines/detail sheet now show task type (Review/Analysis) instead of project name, matching E18-S1's home-feed naming and dropping the "project" concept from the ledger. Analysis detail view surfaces comments-analyzed count via a new `/me/runs` aggregation; publications-analyzed added for Analysis tasks too.
- Custom-period picker rebuilt as a single dark-header month-grid range picker (string-comparison range highlighting on zero-padded `YYYY-MM` keys, no date-math library) replacing the native two-`<select>` picker.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app while building this work.
**Promoted to backlog:** none — the buy-tokens CTA's real wiring is exactly E8-S3's scope, already tracked in Sprint 10.

## [E18-S4] Deep-analysis auto-chain visibility and report styling parity
**Completed:** 2026-07-27
**Handover:**
- **Backfilled at `/sprint-review` time** — see E18-S5's note above and BACKLOG.md's `[E18-S4]` entry for full AC/DoD. Source commits: `762c38f`, `bcd2a89`, `59337ec`, `2deb1e9`.
- New `AnalysisRun.deep_analysis_skip_reason` (migration `f7a8b9c0d1e2`, `insufficient_tokens`/`error`) mirrors `ScheduledRun.last_skip_reason`'s established pattern — root cause of the triggering user report was a genuine `InsufficientTokenBalanceError` (16 items × the D35 15x placeholder multiplier exceeded the user's balance) that simply left no trace anywhere once hit.
- Run feed cards for `deep_analysis` runs now show the chained analysis's own status, not the base run's — a card no longer reads "done" while the analysis behind it hard-failed.
- Separately confirmed via live DEV worker logs: this DEV account's Apify plan tier rejects the `apidojo` comments actor and no `BRIGHTDATA_*` vars are set at all, so every comment fetch currently degrades to zero coverage — an environment/vendor gap, not a code bug, and the reason deep-analysis reports on DEV look content-only today.
- Both the comment-scraper and the worker's auto-chain now log on failure instead of failing silently (same class of fix as the E17 hotfixes below). Report page tabs switched to `TabChip` (matching Review), first tab renamed Статистика→Резюме, gained a 5-line summary card.
**Smoke test:** PASSED — low-balance-skip and forced-chain-failure edge cases confirmed live 2026-07-31 (E19-S1 sweep) on a deliberately underfunded account, alongside the already-passed general auto-chain/status/styling flow (2026-07-28).
**Promoted to backlog:** none new.

## [E18-S3] Scheduled-task cards and dialog parity on the home feed
**Completed:** 2026-07-27
**Handover:**
- **Backfilled at `/sprint-review` time** — see E18-S5's note above and BACKLOG.md's `[E18-S3]` entry for full AC/DoD. Source commits: `f247bbf`, `fd2f9e2`, `1033bc9`, `cb918ad`, `afe1d4e`, `02becd6`, `c8023c1`.
- Home-feed schedule cards brought to full parity with the per-project design (scope/count summary, day/time, last-run date, status, notify badge, 3-dot menu); tapping one now opens `ScheduledRunDialog` (moved into `components/` so home feed and per-project page share it) instead of navigating away.
- `ScheduledRunDialog` brought in line with E18-S2's `RunDialog` redesign (collapsed competitors button + add-new action, toggle-switch once/recurring).
- A once-mode schedule that fired successfully now disappears from both lists (`SCHEDULE_LIST_VISIBLE` shared predicate); a skipped one stays visible with its reason.
- Recurring theme across this whole commit cluster: several back buttons (competitors, run-detail, usage, deep-analysis report) still pointed at pre-E18-S1 project-shell routes with no path leading in — fixed to point at `/`. Any future page still linking to `/projects/[id]/details` or `/results` is the same bug class.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
**Promoted to backlog:** none new.

## [E18-S2] Run-creation flow rebuild (FAB shape, competitors step, recurring toggle)
**Completed:** 2026-07-27
**Handover:**
- **Backfilled at `/sprint-review` time** — see E18-S5's note above and BACKLOG.md's `[E18-S2]` entry for full AC/DoD. Source commits: `b330e8a`, `19c4875`, `a45dc69`, `72ebd1a`, `500a700`.
- FAB back to a circle; competitors step collapses to one button (all selected by default) leading into the picker, which now also lets the user add a brand-new competitor inline (real backend account, auto-selected for this run, also visible on the Competitors page afterward).
- Once/recurring became a single toggle switch. Run cards dropped the project-name line in favor of live KPI figures (competitors/publications always, comments once known) via new fields on `GET /me/run-feed`.
- `500a700` (2026-07-28) restored hairline dividers between the dialog's three step blocks that an earlier commit in this same cluster had removed — direct user-review feedback.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
**Promoted to backlog:** none new.

## [E18-S1] Run-centric navigation overhaul (unified run feed + FAB)
**Completed:** 2026-07-27
**Handover:**
- **Backfilled at `/sprint-review` time (2026-07-28)** — this story and E18-S2..S5 above were implemented 2026-07-26 through 2026-07-28 with no story IDs, no BACKLOG.md entries, and no DONE.md handovers at the time. Found only because this sprint review's mandatory untracked-fix scan (`git log <since-last-review>..HEAD`) turned up 26 commits changing the app's entire navigation shape. Backfilled per direct user request rather than left undocumented — see BACKLOG.md's 2026-07-28 note and `[E18-S1]` entry for full AC/DoD. Source commits: `1820251`, `3435bb0`, `647812d`, `0168d53`, `9c01c0b`, `0cb0722`.
- Home screen (`/`) became a unified cross-project run feed (`GET /me/run-feed`) with a FAB opening a run-type picker (Ревью/Анализ launchable; Разбор конкурента/публикации stay inactive teasers). New `run_type` column on `analysis_runs`/`scheduled_runs` (migration `e3f4a5b6c7d8`).
- Picking Анализ now auto-chains: the worker detects `run_type="deep_analysis"` on completion and immediately starts + enqueues the E17 deep-analysis pipeline, no separate user step.
- **This supersedes E13's entire bottom-nav/tab-bar IA** — Детали/Результаты/Анализ tabs are gone; Competitors moved to the burger menu, Runs to the home feed. Any future work referencing the old tab bar is working from a stale mental model.
- `9c01c0b` (same day) fixed a real regression: the initial nav-overhaul commit shipped with an unlinted E501 failure that silently blocked `deploy-dev` (CI-gated) for every push until caught — a reminder that a large nav-shaped commit is exactly where a fast, unlinted push slips through.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (this is the app's primary navigation surface, used continuously while building the rest of E18).
**Promoted to backlog:** none new — E8-S3 (Sprint 10) already covers wiring E18-S5's buy-tokens CTA stub to a real payment flow.

## [E17 hotfix 3] Hard-failed deep analyses now refund in full
**Completed:** 2026-07-25
**Handover:**
- Both real DEV test runs so far failed and neither refunded its 60-token charge — user flagged this directly ("tokens consumed both times... no results available"). E17-S9 already refunds *partially* on thin comment coverage (still delivers a degraded report), but a hard failure delivering *zero* report never refunded anything at all — an oversight from E17-S1/S4, not something any story's AC ever addressed.
- Consolidated three separate, duplicated fail-and-stop code paths into one: `services/deep_analysis.py:fail_deep_analysis` (previously defined but never actually called anywhere) is now the single place a deep analysis transitions to `failed` — it refunds `tokens_charged` in full onto `user.token_balance` and zeroes `analysis.tokens_charged` so `/me/runs` reflects the true amount kept. `deep_analysis_synthesis.py`'s local `_fail()` helper (4 call sites) and `worker.py`'s outer `except Exception` catch-all both now call it instead of hand-rolling the same three field assignments.
- 3 tests updated/added to assert the refund (`test_synthesize_report_no_done_items_fails_without_api_call`, `test_synthesize_report_api_error_marks_failed`, `test_process_deep_analysis_exception_marks_failed`).
- **Not applied retroactively**: the two already-failed DEV test rows from earlier today still show `tokens_charged=60` unrefunded, since this logic wasn't live when they failed. Asked the user whether to hand-correct that via direct SQL on DEV — declined (test data, not worth the manual DB write). Any *new* failure from this point on refunds automatically.
- Full suite 282 passed, ruff/mypy/tsc/next-lint clean (no frontend changes this round).
**Smoke test:** user-driven, pending a clean end-to-end pass.
**Promoted to backlog:** none new.

## [E17 hotfix 2] Second DEV smoke-test pass — synthesis call rejected by real API
**Completed:** 2026-07-25
**Handover:**
- With the extraction retry fixed, a second real run got past extraction (all 4 items `done`) but still failed, now at synthesis, with the generic `_UNPARSEABLE_MESSAGE_RU` fallback. `synthesize_report`'s `except Exception` swallowed the real error with no log line — same silent-failure shape as the first bug, just one stage further downstream.
- Diagnosed by replaying the exact call (`deep_analysis_synthesis.SYSTEM_PROMPT` + `REPORT_TOOL`, forced `tool_choice`) against the real Anthropic API using the DEV worker's own key (via `railway variables`): `BadRequestError: temperature is deprecated for this model`. `claude-sonnet-5` rejects the `temperature` param entirely — Haiku (used for extraction/summaries) doesn't have this restriction, which is why only the synthesis call was ever affected. Confirmed the fix by re-running the same replay without `temperature`: real `tool_use` response came back correctly.
- Fix: removed `temperature=0.3` from the one `messages.create` call in `deep_analysis_synthesis.py`.
- Also added `logger.exception(...)` in that `except` block (stdlib `logging`, matching the convention already used in `telegram_notify.py`/`telegram_webhook.py`) — this failure mode has now cost two rounds of blind DB-querying-plus-manual-API-replay to diagnose; a log line makes the next one visible in `railway logs` directly.
- Separately fixed a raw-key toast (`Analysis.genericError` rendered untranslated) spotted in the same screenshot — the `Analysis` i18n namespace was missing a `genericError` key that `analysis/page.tsx`'s error handler references.
- Full suite still 282 passed, ruff/mypy/tsc/next-lint/next-build all clean.
- Deployed to DEV only. Re-test pending.
**Smoke test:** user-driven, in progress across two rounds now.
**Promoted to backlog:** none new.

## [E17 hotfix] First real DEV smoke test — 3 bugs found and fixed
**Completed:** 2026-07-25
**Handover:**
- E17 deployed to DEV (`5be4686`), user ran a real deep analysis against a live IG account. It failed, and surfaced three real bugs no amount of unit testing had caught (mocks all returned well-formed data by construction):
  1. **Extraction silently failed for every item.** `_parse_extraction` did a bare `json.loads` with no tolerance for markdown code fences, and `_extract_item`'s retry loop only retried on network/API exceptions — a single malformed response permanently failed that item with no retry and no log line. Confirmed via direct DEV DB query (`railway connect Postgres`): all 4 `deep_analysis_items` rows were `status=failed` despite `comments_analyzed_count=10` proving comments were fetched fine, which pointed at the parse step specifically rather than comment scraping. Fixed: `_parse_extraction` now strips leading/trailing ` ``` ` fences before parsing, and the retry loop now retries on an unparseable response too (not just exceptions) — while still billing a `UsageEvent` for every real API response returned, parseable or not, since tokens were genuinely spent either way (this is why `synthesize_report` then failed with "нет публикаций для анализа": zero `done` rows to synthesize from).
  2. **Failed analyses were unopenable.** `analysis/page.tsx`'s history list only made a card clickable when `status === "done"`; a `failed` card had no `onClick` and no visual affordance, even though the report page already handled `failed` correctly (`error_message` display existed and worked, just unreachable). One-line fix: `openable` now includes `"failed"`.
  3. **Deep-analysis token charges were invisible in the wallet.** `/me/usage` (the "Потрачено за период" screen) is powered by `/me/runs`, which only ever queried `AnalysisRun` — `DeepAnalysis` rows were never included, so the 60-token deep-analysis charge silently vanished from the user-facing ledger even though `user.token_balance` was correctly debited. Fixed by unioning both sources into `RunSummaryOut` (new `kind`/`tokens_charged` fields), sorted together by `created_at`; frontend shows a "· Разбор запуска" suffix on deep-analysis rows and uses `tokens_charged` (not `progress_items`) for both the per-row amount and the period total, so E17-S9 refunds are reflected correctly too.
- New backend test `test_my_runs_includes_both_runs_and_deep_analyses`; updated `test_extract_unparseable_response_stores_failed_but_still_charges_usage` to assert 3 retried attempts × 2 usage events (was asserting the old no-retry behavior).
- Full suite 282 passed (was 282; net +1/-0 after the retry-count test update), ruff/mypy clean. `next lint`/`tsc --noEmit`/`next build` clean.
- Deployed to DEV only (`git push origin main`) — not tagged for PROD. PROD was already bumped separately to `v0.6.0` (pre-E17 state) earlier the same session, per the standing DEV-first-then-tag workflow.
**Smoke test:** user-driven — this whole fix exists because of one. Re-test pending on DEV.
**Promoted to backlog:** none new — this was pure bug-fixing on already-scoped E17 work.

## [E17-S9] Thin-comment-data fallback and partial pricing
**Completed:** 2026-07-25
**Handover:**
- Coverage measured in `synthesize_report` from the already-loaded `DeepAnalysisItem` rows: share with `comments_analyzed_count > 0`. Below `deep_analysis_comment_coverage_threshold` (new config, default 0.5): `_strip_comment_derived_sections` mutates the response **after** it comes back from Claude (clears `sentiment_summary`/`representative_quotes`/`faq_pack`, sets `comment_coverage_degraded: true` on both `stats`/`recommendations`) — a post-hoc strip guarantees no fabricated content regardless of what the model actually produced, stronger than a prompt instruction alone.
- `_apply_thin_coverage_pricing` refunds `tokens_charged - ceil(tokens_charged * deep_analysis_thin_coverage_multiplier)` (new config, default 0.5) onto `user.token_balance` and rewrites `tokens_charged`. Has to be a refund-after-the-fact, not a smaller up-front charge, since E17-S1 charges at creation time before comment coverage is knowable.
- `api/deep_analyses.py` needed no code change — confirmed, not skipped — since `DeepAnalysisOut` already passes the JSONB fields straight through.
- Frontend: new optional `comment_coverage_degraded` flag on both report types; one shared `AlertTriangle` warning banner above the segmented control when set, covering both tabs from one check. `next build` re-run clean.
- **Test-fixture bug found and fixed** (not production): tests shared one mutable `_VALID_REPORT` dict across the file; the degraded test's in-place mutation was leaking into later tests. Fixed with `copy.deepcopy` in the test's response builder — production is unaffected since the real SDK returns a fresh object per call.
- `docs/PROMPTS.md` gained a note on the strip/refund happening outside the prompt itself.
- 2 new backend tests; ruff/mypy clean; full suite 281 passed (was 279). `tsc`/`eslint`/`next build` clean.
- **This closes the entire E17 epic (E17-S1→S9, 9/9 stories)**, done back-to-back in one session per direct user request.
**Smoke test:** PARTIALLY CONFIRMED, closed by user choice — 2026-07-31 (E19-S1 sweep): the reduced token charge on thin comment coverage is confirmed live. The degrade banner itself was not observed on the tested run; user explicitly said its absence doesn't bother them, so this is accepted as-is rather than investigated further.
**Promoted to backlog:** `GET /items/{id}` gap (from E17-S8); reading a real pilot run's `usage_events` to set the real token multipliers per D35

## [E17-S8] Report page: Рекомендации tab
**Completed:** 2026-07-25
**Handover:**
- Content-idea cards, do-more/do-less, hook templates, FAQ pack, posting-schedule all render as conditional sections in the same report page as E17-S7's Статистика tab.
- **Deliberate scope deviation, logged not hidden:** the AC's "steal-this shortlist reuses `results-cards` visuals" would mean full `ContentCard`s, but `steal_this` only carries `{content_item_id, reason}` and there's no `GET /items/{id}` endpoint anywhere in this codebase to fetch one item by id — building that was out of this story's frontend-only file list. Shipped a lightweight reason-only card that deep-links into the run's Publications tab instead (the real `ContentCard` is one tap away there).
- That deep-link needed a real fix: `runs/[runId]/page.tsx`'s tab state was local-only, so `?tab=publications` did nothing until this story added `useSearchParams()` as the initial-state source.
- Ran a full `next build` (not just typecheck/lint) specifically to confirm the new `useSearchParams()` usage doesn't hit Next's static-prerender Suspense requirement — confirmed fine since the route is dynamic (`ƒ`), not static.
- `tsc --noEmit`/`next lint`/`next build` all clean.
- **This closes the E17 epic's core report UI** (E17-S1→S8). E17-S9 (thin-comment-data fallback) is the remaining stretch story.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (this page's UI is part of the redesigned deep-analysis report the user has been using directly).
**Promoted to backlog:** a real `GET /items/{id}` endpoint would let steal-this render full `ContentCard` visuals as originally specced

## [E17-S7] Report page: Статистика tab
**Completed:** 2026-07-25
**Handover:**
- New route `deep-analyses/[analysisId]/page.tsx` — polls the report every 5s while in progress, then renders the `Segmented` Статистика/Рекомендации control once `done`.
- Topics render as a ranked card list with heat badges (`VIRALITY_STYLE`, reused from `results-cards.tsx`) — not a chart, per the mobile card mandate; `avg_virality: "unknown"` renders no badge. Formats/hooks as chip counts, CTA share as a mono percentage, cadence/sentiment as prose, representative quotes as quote rows.
- Every section is independently conditional on having data — generic graceful-empty handling now; E17-S9 will add an explicit thin-coverage banner once the backend can flag that case specifically.
- Рекомендации tab is a placeholder pending E17-S8 (next in this session).
- `tsc --noEmit`/`next lint` clean.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
**Promoted to backlog:** none

## [E17-S6] Analysis entry point: history + new-analysis picker
**Completed:** 2026-07-25
**Handover:**
- `analysis/page.tsx` gained a local `view: "teaser" | "history"` state instead of a new route — clicking «Разбор запуска» (the only enabled teaser card) switches to a history list in place. Rows use the existing `StatusPill` dot+chip pattern (`RUN_STATUS_PILL`/`DOT`), mirrored as new `DEEP_ANALYSIS_STATUS_PILL`/`DOT` in `lib/format.ts`. A `done` row links to `/projects/[id]/deep-analyses/[analysisId]` (E17-S7's route).
- **Deviation logged, not silently claimed:** the AC's "unified Sheet component (DESIGN_SYSTEM §4/§6)" refers to a not-yet-built consolidated `BottomSheet` — §6 itself lists 4 separate implementations still needing unification, an app-wide item out of this story's scope. `deep-analysis-sheet.tsx` follows the established `run-dialog.tsx` self-contained-modal pattern instead, visually matching the spec.
- In-progress state: new analysis prepended to the list on creation; a 5s poll (mirrors `schedule-alerts.tsx`'s lightweight pattern, not `run-tracker.tsx`'s full context) refreshes while any row isn't `done`/`failed`.
- Cost preview uses E17-S5's `estimate` endpoint. `ru.json` gained a `DeepAnalysis` namespace (also pre-added S7/S8's key set in the same edit).
- `tsc --noEmit`/`next lint` clean (no frontend test suite in this repo, per CONVENTIONS.md).
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
**Promoted to backlog:** consolidate the four bottom-sheet implementations into one shared component (pre-existing DESIGN_SYSTEM §6 item)

## [E17-S5] Deep Analysis API
**Completed:** 2026-07-25
**Handover:**
- New `backend/src/api/deep_analyses.py` — `POST /projects/{project_id}/runs/{run_id}/deep-analyses` calls E17-S1's `start_deep_analysis` (400 `run_not_done` / 402 `insufficient_token_balance` on its two exceptions, same shape `api/runs.py:create_run` uses), commits, then enqueues the E17-S4 worker pipeline via new `services/queue.py:enqueue_deep_analysis`. `GET /projects/{id}/deep-analyses` (history, most recent first) and `GET /deep-analyses/{id}` (status/report) are plain reads through `get_owned_project`, same 404-collapses-existence pattern as every other router.
- `DeepAnalysisOut` exposes `report_stats`/`report_recommendations` as raw JSONB passthrough — E17-S6/S7/S8's frontend renders directly, no reshaping.
- Router registered in `main.py`. 7 new tests (`test_deep_analyses_api.py`) covering create (success/run-not-done/insufficient-balance/foreign-run-404), list ordering, and get (done-with-report / missing-or-foreign-404).
- **This closes E17's backend half (E17-S1→S5)** — the full pipeline is reachable end-to-end from a real HTTP request. E17-S6 onward is frontend.
- **Changelog addition (found necessary during E17-S6):** read-only `GET /projects/{project_id}/runs/{run_id}/deep-analyses/estimate` (reuses `compute_tokens_charged` without deducting) — S6's new-analysis sheet needs a pre-charge token number, which `POST .../deep-analyses` can't provide since it only returns `tokens_charged` after charging.
- ruff/mypy clean; full suite 279 passed (was 271).
**Smoke test:** PASSED (general create/poll/list flow — confirmed via the user's own manual click-through, 2026-07-28; cross-user 404 isolation confirmed 2026-07-31 via existing automated coverage — `test_create_deep_analysis_404_for_foreign_run` and `test_get_deep_analysis_404_for_missing_or_foreign` in `test_deep_analyses_api.py` already assert this on every CI run, so no live second-account click-through was needed).
**Promoted to backlog:** none

## [E17-S4] Synthesis pass — full report (Sonnet)
**Completed:** 2026-07-25
**Handover:**
- New `backend/src/services/deep_analysis_synthesis.py:synthesize_report` — queries `done`-status `DeepAnalysisItem` rows joined to `ContentItem`/`Account`/the run's virality baseline (`services/metrics.py`), makes one forced tool-use call (`REPORT_TOOL` schema) to `deep_analysis_synthesis_model` (`claude-sonnet-5`, D33's only non-Haiku call). The tool's `.input` is already a parsed dict — no `json.loads` needed, which is what "structured output, not free text" meant.
- Never raises: zero `done` items, an API exception, a missing `tool_use` block, or a tool input missing `stats`/`recommendations` all set `status=failed` + a Russian `error_message` + `completed_at` via an internal `_fail()` helper — mirrors `generate_run_summary`'s never-raises contract.
- `worker.py` gained the thin-wrapper/core split (mirrors `process_run`/`run_analysis`): `process_deep_analysis` drives `extracting` → E17-S3's extraction → `synthesizing` → this story's synthesis, with an outer try/except marking `failed` on any uncaught exception. `run_deep_analysis` is the registered arq job — **not yet enqueued anywhere**, that's E17-S5.
- `docs/PROMPTS.md` gained the synthesis prompt + tool schema.
- 6 new tests (`test_deep_analysis_synthesis.py`) + 2 new tests (`test_worker.py`'s `process_deep_analysis` status transitions and exception handling).
- **For E17-S5:** `process_deep_analysis`/`run_deep_analysis` are ready to enqueue; the endpoint just needs `start_deep_analysis` (E17-S1) then `enqueue_job("run_deep_analysis", ...)`.
- ruff/mypy clean (one `# type: ignore[call-overload]` on the tool-use call, matching the existing SDK-typing-gap precedent in `summarizer.py`); full suite 271 passed (was 263).
**Smoke test:** PASSED (plausible-report generation — confirmed via the user's own manual click-through, 2026-07-28; forced-malformed-response → `failed` path confirmed 2026-07-31 via existing automated coverage — `test_synthesize_report_malformed_tool_input_marks_failed` and `test_synthesize_report_missing_tool_use_marks_failed` in `test_deep_analysis_synthesis.py` already force both failure shapes on every CI run).
**Promoted to backlog:** none

## [E17-S3] Per-item extraction pass (Haiku)
**Completed:** 2026-07-25
**Handover:**
- `deep_analysis_items` table (migration `d2e3f4a5b6c7`): one row per `(deep_analysis_id, content_item_id)`, `status` (`done`/`failed`), content-signal columns (`topic`/`content_format`/`hook_type`/`has_cta`) plus comment-derived columns (`sentiment`/`complaints`/`praises`/`questions`/`notable_phrases`), and `comments_analyzed_count` (the coverage signal E17-S9 will threshold on).
- New `backend/src/services/deep_analysis_extraction.py:extract_deep_analysis_items` — fetches each item's comments via E17-S2's `fetch_comments`, then reuses `summarizer.py`'s concurrent-semaphore/Message-Batches split verbatim (same `summary_batch_threshold`/`summary_concurrency` config — no new D29 threshold to drift). Deliberately imports `summarizer.py`'s private `_fetch_image_block` rather than duplicating the resize/skip-large-caption logic.
- Output is `json.loads`-parsed (structured JSON per the AC, not the run-summary's regex protocol). Important distinction covered by two separate tests: an **unparseable response is still billed** (the API call happened), but **exhausted retries are not** (no successful call at all).
- `docs/PROMPTS.md` gained the extraction prompt; `tests/conftest.py` gained `make_deep_analysis()`.
- 6 new tests. Migration verified with a real upgrade/downgrade/upgrade round-trip. ruff/mypy clean; full suite 263 passed (was 257).
- **For E17-S4:** `DeepAnalysisItem` rows for a `deep_analysis_id` are the complete synthesis input — no comment re-fetch needed.
**Smoke test:** PASSED — 2026-07-28, confirmed indirectly via the user's own manual click-through (extraction completing is a precondition for the reports the user has seen render correctly).
**Promoted to backlog:** none

## [E17-S2] Comment scraping: Apify `apidojo` actor primary, Bright Data fallback
**Completed:** 2026-07-25
**Handover:**
- New `backend/src/services/comment_scraper.py`: `ApifyCommentsClient` (primary, `apidojo/instagram-comments-scraper-api`, `startUrls`/`resultsLimit` input, 3-attempt retry mirroring `platforms/instagram.py`) and `BrightDataCommentsClient` (fallback, Bright Data's trigger→poll→snapshot Dataset API shape). Top-level `fetch_comments(session, item, user_id, settings, apify_client=None, brightdata_client=None)` tries primary then fallback and never raises — both failing returns `[]` with no usage_events written (E17-S9's degrade path).
- `usage_events` gains `apify_comment_result`/`brightdata_comment_result` kinds. A successful primary fetch always writes a flat post-query row, plus an overage row only when the comment count returned exceeds the 15-included threshold (D32). A successful fallback fetch writes one `brightdata_comment_result` row.
- **D36 (new):** comments are always sorted client-side by `likes` descending before truncating to the cap. The AC's empirical spike (does `apidojo`'s "ranking status" field already reflect engagement order?) wasn't run live — no Apify/Bright Data network access in this sandbox — but sorting is correct either way, so it shipped as the default rather than blocking on sandbox access it doesn't have.
- New config (`apify_comments_actor_id`, `apify_comment_query_cost_usd`, `apify_comment_included_comments`, `apify_comment_overage_cost_usd`, `brightdata_api_token`, `brightdata_api_base_url`, `brightdata_ig_comments_dataset_id`, `brightdata_comment_request_cost_usd`); `ENV.md` gained the two Bright Data rows.
- 5 new tests (`test_comment_scraper.py`) against two new fixtures, covering normalization, primary success + both usage rows, fallback-on-failure, both-vendors-fail, and the Bright Data request shape. `httpx.AsyncClient` mocked the same way `test_telegram_notify.py` already does (no new test-mocking pattern introduced).
- **For E17-S3:** `fetch_comments` is ready to call per item during the extraction pass.
- ruff format/check + mypy clean; full suite 257 passed (was 253).
**Smoke test:** PASSED — 2026-07-31 (E19-S1 sweep): user confirmed the primary `apidojo` comment-fetch path now works on real DEV data — the previously-known gap (this DEV account's Apify plan tier rejecting the actor) is resolved. Bright Data fallback specifically not separately force-tested (would need a deliberately broken primary actor id to trigger it), but the priority blocking gap this line tracked is closed.
**Promoted to backlog:** none

## [E17-S1] Deep analysis schema, pricing config, and token-charge plumbing
**Completed:** 2026-07-25
**Handover:**
- Direct user request: run the whole E17 (Run Deep Analysis) epic back-to-back, out of the locked sprint order (E17 was proposed for Sprint 11, unlocked; Sprint 10/E8-S3 monetization is still nominally "next" per SPRINT.md but untouched by this session).
- `deep_analyses` table (migration `c1d2e3f4a5b6`, head after `b3c4d5e6f7a8`): id, run_id, project_id, requested_by, status enum (`pending`/`extracting`/`synthesizing`/`done`/`failed`), tokens_charged, report_stats/report_recommendations (JSONB, both nullable until synthesis), error_message, created_at, completed_at. `deep_analysis_items` (E17-S3) is a separate table/migration, not part of this one.
- New `backend/src/services/deep_analysis.py` — `compute_tokens_charged` (pure, `ceil(items_count * deep_analysis_token_multiplier)`), `start_deep_analysis` (validates `run.status == done`, deducts tokens up front, creates the `pending` row; deliberately does **not** enqueue the worker pipeline — mirrors `api/runs.py:create_run`'s split between the DB write and `enqueue_run`, so E17-S5's endpoint just calls this then enqueues), `fail_deep_analysis` (sets `failed` + `completed_at`, reused by E17-S3/S4 so no row is ever left stuck mid-pipeline).
- Config: `deep_analysis_token_multiplier` (float, default 15.0 — explicitly commented as a D35 placeholder, not a real price) and `deep_analysis_comments_per_post` (25, per D34).
- `RunNotDoneError`/`InsufficientTokenBalanceError` are plain exceptions from the service, translated to HTTPExceptions at the router layer — same pattern as `services/projects.py:ProjectNotFoundError`.
- 4 new tests in `test_deep_analysis_model.py` (roundtrip/defaults, token-rounding, run-not-done rejection, insufficient-balance rejection with balance left untouched, successful deduction). `test_models.py`'s `test_schema_has_exactly_expected_tables` updated. Migration verified with a real upgrade/downgrade/upgrade round-trip against local Postgres. `ruff format`/`ruff check`/`mypy src` clean; full suite 253 passed (was 252).
- **For E17-S2:** `deep_analysis_comments_per_post` config is ready to consume as the per-post comment cap.
**Smoke test:** PASSED — insufficient-balance rejection confirmed live 2026-07-31 (E19-S1 sweep) on a deliberately low-balance account, alongside the already-passed sufficient-balance path (2026-07-28).
**Promoted to backlog:** none

## [E14-S6 follow-up 2] Richer bot message, live token-balance header, dead DEV/PROD link fixed
**Completed:** 2026-07-25
**Handover:**
- **Bot message content:** `telegram_notify.py:notify_run_complete` now sends, for a successful run: accounts/items counts, the run-level AI overview (`run.summary_text`, E15-S1), a plain-text "Топ публикации" list (same virality ranking as the run detail page's Summary tab, no KPI numbers — just handle + one-line caption + a link per post), the results-page link, and the user's post-run token balance. Failure messages keep just the error + balance. All free text (AI summary, item captions, handles, error message) is now `html.escape()`d before going into the HTML-parse-mode message — previously a caption containing `<`/`&` would have silently killed the *entire* notification (Telegram rejects unparseable HTML), which became a real risk once AI-generated captions were added to the message body.
- New `_top_items_lines()` in `telegram_notify.py` reuses `services/metrics.py`'s existing virality-ranking SQL (same subquery/expr helpers `api/items.py`'s `/runs/{id}/top-virality` endpoint uses) rather than duplicating the ranking logic — deliberately not refactored into a shared function across both call sites since the two callers need different projections (full `ContentItemOut` vs. three plain-text fields) and there's no third caller yet.
- `notify_run_complete` signature gained a `session: AsyncSession` param (needed for the top-items query) — updated all 3 call sites in `worker.py` and the two test files that call/mock it (`test_telegram_notify.py`, `test_scheduled_runs.py`'s `mock_notify.await_args.args` unpack).
- **Header token balance not live:** `frontend/lib/run-tracker.tsx`'s existing 3s poll loop now calls `useAuth().refreshUser()` (already existed, just unused for this) whenever any tracked run transitions into done/failed — the header's balance chip was previously only ever refreshed by navigating to `/usage`, so it looked stale for however long the user stayed on the results page after a run finished. No new polling added, just reusing the loop that was already ticking.
- **Dead link in the Telegram message (root cause):** `WEB_URL` was set on the Railway `api` service but never on `worker` — since `notify_run_complete` runs in the worker process, the link fell back to the code default `http://localhost:3000/...`, unreachable from the user's phone. Confirmed via `railway variables --service worker --kv` in both environments (only `RAILWAY_SERVICE_WEB_URL`, the platform-injected one, was present — not the app's own `WEB_URL`). Fixed by setting `WEB_URL` on `worker` in both DEV (`https://web-dev-99e3.up.railway.app`) and PROD (`https://web-production-1bd7f0.up.railway.app`) via Railway CLI, with the user's explicit go-ahead. `ENV.md`'s `WEB_URL` row now calls out that it must be set on **both** `api` and `worker`, so this doesn't regress.
- Per explicit user instruction, also added a line to `CLAUDE.md`'s Hard constraints: agents should no longer verify frontend changes with the Browser tool / scratch-preview routes — the user does their own smoke-test pass before shipping and flagged this as costing too much session time. `tsc`/`eslint` remain the bar for frontend changes; visual verification only on explicit request.
- Backend: added `_top_items_lines` DB-backed test (real virality ranking against Postgres, mirrors `test_items_api.py`'s existing top-virality test setup) plus an HTML-escaping test; ruff/mypy/full pytest (246 passed; the one new test replaces net-new coverage, `test_auth.py`'s 8 failures are a pre-existing test-order/local-Postgres flake reproduced identically on `main` before this change, unrelated). Frontend: `tsc --noEmit`/`eslint` clean on `run-tracker.tsx`.
**Smoke test:** PASSED (bot message content, results link, header balance on DEV — confirmed via the user's own manual click-through, 2026-07-28) — DEFERRED (the PROD-specific link check specifically; folded into E19-S1).
**Promoted to backlog:** none

## [E14-S6 follow-up] Surface skipped-schedule reasons (notification panel + card badge)
**Completed:** 2026-07-25
**Handover:**
- Root-caused via Railway CLI (`railway environment dev`, `railway logs --service worker`) plus a direct `psql` query through the DEV Postgres proxy: the user's real "why didn't my schedule fire?" report traced to `token_balance = 0` on the account, hitting `_fire_one`'s pre-existing (E14-S2) silent-skip guardrail — confirmed the worker's cron *was* ticking correctly on schedule; this wasn't a bug in this session's E14-S6 work. User is topping up tokens themselves; this story is the follow-up: **make the skip visible instead of silent.**
- `ScheduledRun` gained `last_skip_reason` (`no_accounts`/`no_tokens`/`quota_exceeded`, new `ScheduledRunSkipReason` enum) and `last_skip_at`, migration `b3c4d5e6f7a8` (now head). `_fire_one`'s three existing gates now call a new `_skip()` helper that records the reason instead of just `return None`; a successful fire clears both fields. Editing a schedule (`PATCH`) also clears them (a fresh edit is a fresh intent, not a reason to keep showing a stale warning). Once-mode schedules now deactivate on skip too, not just on success — a "once" schedule was always meant to make exactly one attempt at its target occurrence, and leaving it active after a skip would have silently retried a full week later, contradicting "once."
- New cross-project endpoint `GET /scheduled-runs/skipped` (`alerts_router` in `api/scheduled_runs.py`, separate from the project-scoped `router` since the header notification panel has no single project in scope) — joins `ScheduledRun`→`Project` on the user's workspace, returns every schedule with a non-null skip reason.
- Frontend: new `frontend/lib/schedule-alerts.tsx` (`ScheduleAlertsProvider`/`useScheduleAlerts`, wrapped in root `layout.tsx` alongside `RunTrackerProvider`) polls the new endpoint every 30s (skips are rare/server-side, unlike run progress — no need for run-tracker's 3s cadence) and tracks "seen" per `scheduleId:skippedAt` in localStorage, mirroring `run-tracker.tsx`'s pattern so a schedule that gets fixed and skips again later re-surfaces as unseen. Wired into `(app)/layout.tsx`'s existing bell/drawer: unseen counts combine for the badge dot, and skip alerts render above tracked runs in the same drawer, each linking to `/projects/{id}/scheduled`.
- Also added a persistent danger-colored line directly on the Scheduled Runs page's own card (`scheduled/page.tsx`) — the "flag" the user asked for first, independent of whether the notification panel has been opened.
- 8 new backend tests (skip-reason recorded for each of the 3 gates, once-mode deactivates on skip, successful fire clears a stale skip reason, `ScheduledRunOut` exposes the fields, `PATCH` clears them, the new endpoint scopes to workspace and returns empty when nothing's skipped); `ruff format`/`ruff check`/`mypy src` clean; migration verified with a real upgrade/downgrade/upgrade round-trip against local Postgres; full suite (245 tests) passes.
- Frontend verified visually via a temporary `frontend/app/dev-preview/skip-alert` scratch route: one instance mocking `scheduled/page.tsx`'s fetch to confirm the card's red skip-reason line, a second mocking `/auth/me` + `/scheduled-runs/skipped` and rendering the real `(app)/layout.tsx` to confirm the bell's unseen dot and drawer entry with the warning icon, correct project name, and reason text — both deleted before commit. `tsc --noEmit`/`next lint` clean.
**Smoke test:** DEFERRED, explicitly closed without live verification — 2026-07-31 (E19-S1 sweep): user chose to deprioritize this specific edge case (zero-balance schedule due soon showing the skip badge/bell within one cron tick, clearing after top-up) rather than force it live. Accepted as an open gap, not a blocking one.
**Promoted to backlog:** none

## [E14-S6] Scheduled-run redesign: multi-day schedules, Once/Recurring, per-schedule notify toggle
**Completed:** 2026-07-25
**Handover:**
- Direct user request (out of the locked Sprint 10 order): fix real breakage in the scheduled-runs feature (E14-S1..S5, 2026-07-22) found on first live look — no schedule ever seemed to fire/notify — and redesign the data model from one row per weekday to one row per schedule.
- **Root cause of "no notifications sent":** by inspection, `notify_run_complete`'s 3 call sites in `worker.py` were already correct, gated only on `settings.telegram_bot_token` + `user.telegram_id`. Every E14 smoke test was deferred, so nothing had ever exercised this against a real Telegram token/worker deploy — likely environment (`TELEGRAM_BOT_TOKEN` possibly missing on the `worker` service specifically) rather than a code bug. Separately fixed regardless: scheduled runs previously notified unconditionally like manual runs; they now only notify when the schedule's new `notify_enabled` toggle (default off) is on.
- Schema: `ScheduledRun.day_of_week: int` → `days_of_week: int[]` (one row = one schedule spanning any number of days); new `mode` (`once`/`recurring` — `once` fires exactly one selected day's next occurrence then self-deactivates; `recurring` fires every selected day indefinitely) and `notify_enabled: bool`. New `AnalysisRun.notify_on_complete: bool` (default `true` — manual runs unaffected), set from `schedule.notify_enabled` when a schedule fires. Migration `a1b2c3d4e5f6` backfills old rows losslessly (`days_of_week=[day_of_week]`, `mode=recurring`); verified with a real upgrade/downgrade/upgrade round-trip.
- A first-draft CHECK constraint (`array_length(days_of_week,1) >= 1` to reject empty arrays) was silently broken — Postgres's `array_length` returns `NULL`, not `0`, for a zero-length array, and CHECK treats `NULL` as passing. A test (`test_scheduled_run_empty_days_of_week_rejected`) caught it immediately; fixed with `cardinality(days_of_week) >= 1`.
- Frontend: `run-dialog.tsx`'s Schedule branch and `scheduled-run-dialog.tsx` both reworked to lead with an Once/Recurring segmented control, then weekday chips (single-select under Once, multi under Recurring), time, a permanent "no end date" hint under Recurring, and a Telegram-notify switch (default off) — one API call per save instead of the old per-weekday POST loop. `scheduled/page.tsx` and `details/page.tsx` updated to render the new `days_of_week` arrays.
- Also fixed, per direct user report: the mobile bottom nav's active tab was only distinguished by a subtle icon/text color change — now gets a filled `bg-ink`/`text-lime` pill, matching the pill treatment already used for day-of-week chips elsewhere in the design system. Desktop tab bar already had a strong active state and needed no change.
- **Notable environment finding:** this sandbox has a working local Postgres (previously assumed absent throughout this project — see every prior E14 story's smoke-test deferral). `content_scout_test` didn't exist and was created this session; with it, the full backend suite ran for real for the first time: 238 tests pass, migration round-trip clean, ruff/mypy clean. Future sessions should check whether this persists before defaulting to "DEFERRED."
- Frontend verified visually via a temporary `frontend/app/dev-preview/scheduling` scratch route (mocked `fetch`), confirming the Once/Recurring toggle, multi→single day collapse, notify switch, and bottom-nav pill highlight in the Browser pane; deleted before commit. `tsc --noEmit`/`next lint` clean.
- **Same-session fix (post-review):** the notify switch's knob relied on the browser's "auto" left-position resolution for an absolutely-positioned element, layered with a `translate-x-[22px]` delta — that resolved incorrectly in practice (confirmed via `getComputedStyle`/`getBoundingClientRect`: the knob rendered flush against the track's right edge regardless of on/off state, an actual rendering bug, not a screenshot artifact). Fixed by anchoring `left-0.5` explicitly and using `translate-x-0`/`translate-x-5` as a pure delta on top of it.
- **Same-session follow-up (direct user request):** "tie scheduling to the Telegram account's timezone" — Telegram's Bot API/WebApp `initData` exposes no timezone field at all, so the practical equivalent is the device's own IANA zone, read via `Intl.DateTimeFormat().resolvedOptions().timeZone` (the Mini App runs inside the user's own client). Added `lib/telegram-webapp.ts:detectLocalTimezone()` (falls back to `"Europe/Moscow"` only if `Intl` itself throws) and wired it into both dialogs in place of the hardcoded `"Europe/Moscow"` default — matches `docs/UI_GUIDELINES.md`'s existing "user's local timezone" guideline, which the scheduling feature had never actually implemented. Editing an existing schedule still keeps its stored `timezone` unchanged. Both dialogs now show a "Часовой пояс: {zone} (по времени вашего устройства)" hint for transparency, since there's still no picker (single-timezone-per-schedule MVP scope unchanged, just no longer hardcoded to Moscow specifically).
- Full BACKLOG.md entry: see `[E14-S6]` for complete details.
**Smoke test:** PASSED — 2026-07-31 (E19-S1 sweep): user confirmed a schedule actually fires within its cron window and the Telegram DM arrives.
**Promoted to backlog:** none

## [E14-S5] Telegram notification for scheduled-run completion
**Completed:** 2026-07-22
**Handover:**
- **No production code changed.** E14-S2's `_fire_one` already creates the `AnalysisRun` and calls the same `enqueue_run()` a manual run uses — the arq job that eventually calls `notify_run_complete` has no idea whether the run came from a schedule or a manual click, so there was no schedule-specific call site to add.
- Added `test_scheduled_run_completion_notifies_telegram` to `test_scheduled_runs.py` to prove this end-to-end: fires a due schedule, runs the resulting `AnalysisRun` through the real `process_run`, and asserts `notify_run_complete` is called once with the schedule-originated run and the schedule's `created_by` user.
- `ruff format`/`ruff check`/`mypy src` clean; new test collects correctly (`pytest --collect-only`).
- **This closes the E14 epic and Sprint 9** (scheduled runs: schema, CRUD API + arq cron dispatcher, Scheduled Runs page, Run-now/Schedule choice, Telegram notification). Sprint 10 (E8-S3 monetization) is next, no longer blocked.
**Smoke test:** PASSED — 2026-07-31 (E19-S1 sweep): confirmed alongside E14-S6 — schedule fires within its cron window, Telegram DM arrives.
**Promoted to backlog:** none

## [E14-S4] Wire Run-now / Schedule choice into Details' create-run flow
**Completed:** 2026-07-22
**Handover:**
- `run-dialog.tsx` — new `launchMode: "now" | "schedule"` toggle after the scope picker. `"now"` is the exact pre-existing flow, untouched. `"schedule"` reveals a day-of-week row + `<input type="time">` and calls the new `api.createScheduledRun` (E14-S2/S3) instead of `api.createRun`, reusing the same `accountIds` prop the run flow already had (still always `undefined`/whole-list, per E13-S3 — no new selection UI here).
- New render branch for a post-schedule confirmation ("Расписание создано" + link to `/projects/[id]/scheduled`), alongside the existing form/progress branches — schedules have no in-progress state to poll, unlike runs.
- `ru.json`'s `RunDialog` namespace gained the launch-mode toggle, day/time picker, and confirmation copy.
- `tsc --noEmit`/`next lint` clean. Verified via a temporary `frontend/app/dev-preview/rundialog` scratch route (mocked `fetch`, wrapped in `RunTrackerProvider`): "now" mode unchanged, "schedule" mode reveals pickers + renames the button + shows the confirmation screen — desktop + 375px, no console errors, deleted before commit.
- **This closes the E14 epic (Sprint 9)** except E14-S5 (Telegram notification for scheduled-run completion), which is backend-only.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
**Promoted to backlog:** none

## [E14-S3] Scheduled Runs page (list + create/edit)
**Completed:** 2026-07-22
**Handover:**
- `frontend/lib/api.ts` — `ScheduledRunResponse`/`ScheduledRunRequest` + `listScheduledRuns`/`createScheduledRun`/`updateScheduledRun`/`deleteScheduledRun`. `ScheduledRunRequest` is a full-replace body (create and update both use it), matching the backend's `ScheduledRunIn`.
- `frontend/app/(app)/projects/[id]/scheduled/page.tsx` — schedule cards (day/time, scope + competitor-count summary, last-run date, active-toggle checkbox that PATCHes in place), 3-dot delete menu (same pattern as `competitors/page.tsx`). `ScheduledRunOut` only has `last_run_id`, not a date, so the page resolves display dates by fetching each referenced run via the existing `api.getRun` (deduped, in parallel) rather than adding a new backend join for a handful of schedules per project.
- `frontend/app/(app)/projects/[id]/scheduled/scheduled-run-dialog.tsx` — reuses `run-dialog.tsx`'s day/count scope-mode toggle verbatim, adds a competitor multiselect ("Все конкуренты" default, matching `account_ids: null` = whole list), a day-of-week button row, and a native `<input type="time">`. No timezone picker — always submits `"Europe/Moscow"` (or the schedule's existing value on edit), matching the model default; out of this story's AC and this is a single-timezone RU-only MVP.
- Deliberately does **not** reintroduce per-run competitor selection into the manual "Создать запуск" flow — E13-S3 removed that project-wide. This multiselect is scoped to the *scheduled-run* definition only, per this story's own AC and `ScheduledRun.account_ids`'s design (E14-S1).
- `tsc --noEmit` and `next lint` both clean (no frontend unit test suite in this repo, per CONVENTIONS.md — CI gate is typecheck + eslint). Verified visually via a temporary `frontend/app/dev-preview/scheduled/[id]` scratch route (mocked `window.fetch`, since this page does live API calls): list view, create dialog (scope toggle, multiselect reveal, weekday/time pickers), delete menu — desktop + 375px, no console errors, deleted before commit.
- **For E14-S4:** the scope+multiselect+day/time UI lives self-contained in `scheduled-run-dialog.tsx`; E14-S4 wires its own "Запланировать" branch into `run-dialog.tsx` per its AC rather than reusing this component directly.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (superseded visually by E18-S3's redesign, but the underlying create/edit/deactivate flow has been exercised).
**Promoted to backlog:** none

## [E14-S2] Scheduled runs: CRUD API + arq cron dispatcher
**Completed:** 2026-07-22
**Handover:**
- `backend/src/services/scheduled_runs.py:most_recent_occurrence_utc(schedule, before)` — pure function (no DB, stdlib `zoneinfo`, no new dependency) that finds the most recent UTC instant a schedule's `(day_of_week, time_of_day)` occurred in its own IANA timezone; `is_due(schedule, now_utc, window_minutes)` wraps it. Chose "look back for the most recent occurrence" over "does today's local weekday match" specifically to avoid a midnight-boundary gap — a schedule at 23:58 would never fire under the naive same-day check, since by the next tick the weekday has already rolled over.
- `fire_due_schedules(session, now=None)` — the cron tick's core, testable without arq/Redis. `_fire_one` mirrors `POST /projects/{id}/runs`'s gates (no active accounts, `token_balance <= 0`, `max_runs_per_user_per_day` quota) but skips silently instead of raising an HTTPException, since a cron tick has no user to show an error to. One schedule's exception is caught + rolled back without blocking the rest.
- `WorkerSettings.cron_jobs = [cron(check_scheduled_runs, minute=set(range(0, 60, 5)), second=0)]` (`backend/src/worker.py`) — arq ticks aligned to `:00/:05/:10.../:55`; `TICK_WINDOW_MINUTES = 5` matches that cadence exactly so consecutive windows tile the timeline with no gaps or double-fires.
- `backend/src/api/scheduled_runs.py` — `POST/GET/PATCH/DELETE /projects/{project_id}/scheduled-runs`, mounted via `APIRouter(prefix=...)` like `accounts.py`, registered in `main.py`. `ScheduledRunIn` is a full-replace body shared by POST and PATCH (mirrors `ProjectUpdateIn`'s pattern, not partial-PATCH semantics); validates the XOR duration/item_limit scope (same as `RunRequestIn`) and the timezone string via `zoneinfo.ZoneInfo(...)`.
- `test_models.py:test_schema_has_exactly_expected_tables` updated to include `scheduled_runs` — would have failed CI otherwise.
- 22 new tests in `test_scheduled_runs.py` (6 pure scheduling-math, ran locally with no DB; 16 DB-integration covering CRUD + 6 `fire_due_schedules` scenarios). `ruff format`/`ruff check`/`mypy src` clean.
- **For E14-S3:** `ScheduledRunOut` (incl. `last_run_id`) is ready to consume for the list page.
**Smoke test:** PASSED — 2026-07-31 (E19-S1 sweep): confirmed alongside E14-S6/S5 — the arq cron dispatcher fires a due schedule unattended.
**Promoted to backlog:** none

## [E14-S1] Scheduled runs: schema and migration
**Completed:** 2026-07-22
**Handover:**
- `backend/src/models/scheduled_run.py:ScheduledRun` — mirrors `AnalysisRun`'s XOR `duration_days`/`item_limit` CHECK constraint (`duration_or_item_limit_range`, from E3-S7) plus a new `day_of_week_range` CHECK (0=Monday..6=Sunday, matching Python's `datetime.weekday()`). `timezone` is a plain IANA-name `String(64)` — no new dependency, Python 3.12 stdlib `zoneinfo` resolves it in E14-S2's cron tick — with a Python-side default `"Europe/Moscow"`. `last_run_id` is a nullable FK to `analysis_runs.id`, to be updated by E14-S2's dispatcher after each fire.
- Migration `f6a7b8c9d0e1` (now head, follows `a9b8c7d6e5f4`); single linear chain confirmed via `alembic heads`.
- `make_scheduled_run()` test helper added to `backend/tests/conftest.py`, same shape/pattern as the existing `make_run()`.
- 4 new tests in `backend/tests/test_models.py`: roundtrip + defaults, XOR-rejected, both-set-rejected, day_of_week-out-of-range-rejected. `ruff format`/`ruff check`/`mypy src` clean.
- **For E14-S2:** table is ready — the CRUD API + arq cron tick build directly on top of `ScheduledRun`.
**Smoke test:** PASSED — 2026-07-31 (E19-S1 sweep): user confirmed via direct DB query, screenshots showing `scheduled_runs` rows with `days_of_week` arrays, `mode` (once/recurring), `notify_enabled`, and the XOR `duration_days`/`item_limit` shape all as expected.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (superseded visually by E18-S1's run-feed IA, but the underlying navigation has been exercised continuously since).
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
**Promoted to backlog:** none

## [E15-S2] Top-5-posts-by-virality for a run
**Completed:** 2026-07-22
**Handover:**
- New `GET /runs/{run_id}/top-virality?limit=5` (`backend/src/api/items.py:list_top_virality_items`, `TopViralityOut`) — reuses `ContentItemOut` shape and the existing `virality_baseline_subquery`/`virality_ratio_expr` join from `list_run_items`, filtered to non-null ratios (excludes insufficient-sample items entirely) and ordered desc with a configurable `limit` (1–20, default 5).
- A dedicated endpoint rather than folding into E15-S1's run-summary storage (that story stores fields on `AnalysisRun`, not an endpoint) or the paginated `/runs/{run_id}/items` (different, non-paginated shape).
- 3 new tests in `test_items_api.py`. `ruff format`/`ruff check`/`mypy src` clean. No new dependencies, no ENV vars, no migration.
- **For E15-S3:** this endpoint plus E15-S1's stored summary fields are both ready to consume for the run detail page's Summary tab.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (usage_events pair count not separately DB-verified, but the Balance/Usage page reflects normal token consumption).
**Promoted to backlog:** none

## [E16-S1] Analysis teaser page
**Completed:** 2026-07-22
**Handover:**
- By the time this story started, E13-S1 had already deleted `/create` and stubbed `/analysis` (Sparkles "coming soon"), so the story's originally-listed "read `create/page.tsx`" file no longer existed — read the current `/analysis` stub directly instead. No functional impact.
- `frontend/app/(app)/projects/[id]/analysis/page.tsx` — kept the Sparkles/title/comingSoon block, added a 3-card responsive grid (shared `Card`/`Badge` components) for Разбор конкурента / Разбор запуска / Разбор публикации (the last covers "publication deep-dive + script generation" as one card, matching the existing `comingSoon` copy which already describes it as combined). All cards `opacity-60` + `cursor-not-allowed` + `aria-disabled`, "Скоро" badge, zero click handlers.
- `frontend/messages/ru.json` — `Analysis.cards.{badge,competitor,run,publication}` keys added.
- No backend changes, no new deps, no ENV vars. This closes Sprint 8's E16 epic — E15-S1/S2/S3 (run detail: AI summary, top-5-by-virality, Summary+Publications tabs) are next.
- typecheck + eslint (the CI gate) both clean. Verified visually via a temporary `frontend/app/dev-preview/analysis` scratch route (direct import of the real page component), screenshotted at desktop + 375px, deleted before commit.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through (this page/tab is now superseded by E18-S1's FAB picker, but was exercised while live).
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
**Promoted to backlog:** none

## [E13-S2] Details dashboard: KPI card, nav links, run-history cards, create-run entry
**Completed:** 2026-07-22
**Handover:**
- New `GET /projects/{project_id}/stats` (`backend/src/api/projects.py`, `ProjectStatsOut.lifetime_items_analyzed`) — `SUM(AnalysisRun.progress_items)` across all runs for the project, any status, via `func.coalesce(..., 0)`; scoped through the existing `_get_owned_project` 404 pattern. `frontend/lib/api.ts`: `ProjectStatsResponse` + `api.getProjectStats`.
- `frontend/app/(app)/projects/[id]/details/page.tsx` replaces the E13-S1 placeholder: KPI card (competitors count from the existing accounts list + lifetime items from the new stats endpoint, 2-column grid built to add more stats without a layout change), full-width nav rows to Конкуренты and Запланированные запуски (`/scheduled` — 404s until E14-S3 ships, expected), run-history cards (date/accounts/publications/tokens, clickable to `/results?run=<id>` only when `status === "done"`), and a "Создать запуск" button opening the existing `RunDialog` against the whole active account list (`accountIds: undefined` — per-run selection is gone as of E13-S3).
- "Tokens consumed" reuses `progress_items` directly — 1 token is debited per scraped publication in this system (`worker.py`), so it's the same number as "publications analyzed", not a separately tracked field.
- New tests: `test_project_stats_sums_items_across_runs`, `test_project_stats_zero_with_no_runs`, `test_project_stats_scoped_to_workspace` in `backend/tests/test_projects.py`. ruff/mypy/tsc/next-lint all clean locally; pytest itself needs the CI Postgres service (no local DB in this sandbox, consistent with every prior story here).
- `/history` route (run table + shortlist history) is unchanged and now partially redundant with Детали's run cards — flagged as a cleanup candidate once E15-S3 (run detail view) exists and nothing links to `/history` anymore.
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (superseded visually by E18-S1's run feed, but the underlying KPI/stats endpoint was exercised while this page was live).
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (this tab bar is now superseded by E18-S1's run feed, but was exercised while live).
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app.
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own ongoing use of the live Telegram bot (this is the app's core access/notification path, exercised continuously since).
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own ongoing use of the live Telegram Mini App (this is the app's primary access path, exercised continuously since; also independently confirmed live at E8-S6).
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
**Smoke test:** PASSED — 2026-07-28, confirmed via the user's own manual click-through of the live app (bottom nav since superseded by E18-S1's run feed, but the mobile card/toast/skeleton patterns are still in active use).
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
**Smoke test:** PASSED — local browser at 375px + 1280px, plus this v1 skin has been in live DEV use since; fully superseded by the v2 «Acid Instrument» design system (D31, shipped via E18).
**Promoted to backlog:** none

## [E4-S3] Claude cost optimization — 2026-07-19
**Handover:**
- Image resize: `settings.summary_image_max_side` (default 512, was 1024); `_fetch_image_block` accepts optional `settings` param
- Skip image: `_build_content_blocks` omits image when `len(caption) > settings.summary_skip_image_caption_chars` (default 200)
- Cross-run reuse: `_reuse_summary_if_available(session, item, project_id, run_id)` copies summary from most recent prior same-project same-external_id item; `summarize_run_items` accepts optional `project_id`; worker passes `run.project_id`
- Batch path: `_summarize_via_batches` triggered when pending items ≥ `summary_batch_threshold` (default 20); polls `client.messages.batches.retrieve()` until `processing_status == "ended"`, iterates `await client.messages.batches.results(id)` with `custom_id = str(item.id)` mapping; exception → falls back to concurrent path
- 6 new tests in `backend/tests/test_summarizer.py`; 4 prior tests still pass
**Smoke test:** DEFERRED — 2026-07-28 review: needs a deliberate twice-back-to-back run comparison to confirm the token-usage reduction, not something general use demonstrates on its own; folded into the trimmed E19-S1 sweep.

## [E7-S4] Pilot security guardrails — 2026-07-19
**Handover:**
- **SUPERSEDED same day (2026-07-19, commit `053cbe3`):** the invite-code gate described in the next bullet was removed hours after this story shipped — registration is open to everyone, new accounts start with `token_balance=50`. See **D39** (backfilled 2026-07-31, found during E19-S1) — this line is kept for history only, do not treat it as current behavior.
- ~~Invite code gate: `REGISTRATION_INVITE_CODE` env var; `GET /auth/register/config` returns `{require_invite: bool}`; register handler checks with `hmac.compare_digest`; frontend register page shows invite field conditionally~~ (removed 2026-07-19, see above)
- Per-user run quota: `MAX_RUNS_PER_USER_PER_DAY` (default 10); counted in UTC day window; 429 with Russian message naming the limit
- Rate limiting: `backend/src/middleware/rate_limit.py` → `check_rate_limit(request, limit=10)` uses Redis INCR+EXPIRE; wired to login and register
- Boot check: `main.py` crashes at startup if `jwt_secret` == insecure default in non-local env
- Security headers: `_SecurityHeadersMiddleware` on API (X-Content-Type-Options, Referrer-Policy); CSP `frame-ancestors` on Next.js (`frame-ancestors 'self' https://web.telegram.org https://*.telegram.org`)
- XLSX formula injection: `_safe_text()` prefixes `=`, `+`, `-`, `@` cells with `'`; applied to account_handle, title, summary
- Login timing: `dummy_verify()` in `passwords.py` (rounds=12); called from `providers.py` on user-not-found path
- Tests: `backend/tests/test_guardrails.py` — 10 tests (3 unit tests pass locally without Postgres; 7 DB tests run in CI)
**Smoke test:** PASSED (rate-limit hammering + formula-injection export, both CI-covered) — the invite-code-rejection check itself is now moot per D39 (registration is intentionally open); replaced 2026-07-31 by `test_register_succeeds_without_invite_code` asserting the current correct behavior.

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
**Smoke test:** PARTIALLY CONFIRMED — re-enqueue/no-duplicate-`content_items` behavior confirmed 2026-07-31 via existing automated coverage (`test_process_run_duplicate_insert_is_noop` in `test_worker.py`). The 8+-account wall-time-vs-sequential timing check is still DEFERRED — split into its own story [E19-S2] so it doesn't block E19-S1's close.
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
**Smoke test:** PASSED — 2026-07-31 (E19-S1 sweep): user confirmed setting `is_admin=true` directly in DEV Postgres correctly unlocks `/admin`.
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
