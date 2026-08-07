# SPRINT.md — content-scout

## Sprint 1 — Walking skeleton

**Goal:** A deployed, authenticated, Russian-language shell: anyone can register on DEV, log in, and see their empty workspace. Schema and CI foundations in place for everything that follows.

**⚠️ Pre-launch reminder:** the `production` Railway environment still needs `RAILPACK_START_CMD` set per-service on `api`/`worker` (same fix just applied to `dev` — see DONE.md E1-S1 handover and ENV.md) before the first `v*` tag is pushed, or `cd.yml`'s deploy will fail the same way `deploy-dev` initially did.

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E1-S1 | Monorepo scaffold, local env, CI, DEV deploy | done |
| E1-S2 | Database schema and migrations | done |
| E1-S3 | Email+password auth and personal workspace | done |

**Sprint 1 complete.**

Full story definitions live in `BACKLOG.md`.

## Sprint 2 — Projects & competitor lists, run lifecycle with mock data

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E2-S1 | Project CRUD | done |
| E2-S2 | Competitor list management (IG, max 50) | done |
| E3-S1 | Run creation, cost estimate, worker skeleton | done |

**Sprint 2 complete.**

## Sprint 3 — Real Apify scraping, Claude summaries, full pipeline

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E3-S2 | Apify Instagram integration and metrics | done |
| E4-S1 | Claude summarization service | done |
| E4-S2 | Summarization in the run pipeline | done |

**Sprint 3 complete.** The full analysis pipeline (scrape → summarize → done) runs end-to-end against real Apify + Claude on DEV.

## Sprint 4 — Results table, XLSX export, shortlist

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E5-S1 | Results table | done |
| E5-S2 | XLSX export | done |
| E6-S1 | Shortlist | done |

**Sprint 4 complete.**

## Sprint 5 — History, usage rollups, admin view

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E6-S2 | Run and shortlist history | done |
| E7-S1 | Usage rollups | done |
| E7-S2 | Admin usage view | in-progress (carry-over — close it first in Sprint 6) |

## Sprint 6 — Hardening, cost cuts, redesign, Telegram test launch

**Goal:** the app is safe and pleasant to share with test users **inside Telegram**: the worker survives full-size runs, strangers can't burn our Apify/Claude budget, Claude cost per item drops ~4× (D29), every screen wears the new light design system (D28), and the app opens as a Telegram Mini App from the bot with zero login friction (D27). **No payments** — Telegram Stars billing (E8-S3) comes after Sprint 6.

**Execution mode:** designed to be run back-to-back autonomously in one or few sessions (`/start-story` → `/finish-story` per story, in order, no user intervention expected). If a story blocks on a missing human prerequisite, note it in the story's Handover, skip forward if independent, and list it in the session summary.

**Human prerequisites (do BEFORE starting the sprint — see ENV.md):**
1. Create the bot: message @BotFather → `/newbot` → pick a name/handle (e.g. `content_scout_dev_bot`). Copy the token.
2. Railway `dev` environment: set `TELEGRAM_BOT_TOKEN` on **api and worker**, and `TELEGRAM_WEBHOOK_SECRET` (any random ≥32-char string) on **api**. (PROD gets its own separate bot later — not needed for Sprint 6.)
3. Railway `dev` **and** `production`: set `REGISTRATION_INVITE_CODE` on **api** (any code you'll share with test users).
   Everything else (webhook registration, menu button) is done by the stories via the Bot API.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E7-S2 | Admin usage view — carry-over: verify, smoke-test, finish-story | done |
| 1 | E3-S6 | Worker resilience and parallel scraping (critical bug fix) | done |
| 2 | E7-S4 | Pilot security guardrails (critical) | done |
| 3 | E4-S3 | Claude cost optimization | done |
| 4 | E12-S1 | Design system re-skin (light theme v1) | done |
| 5 | E12-S2 | Mobile cards, bottom navigation, UX states | done |
| 6 | E8-S1 | Telegram Login | done |
| 7 | E8-S5 | Telegram Mini App shell (no billing) — **sprint exit criterion** | done |
| 8 | E8-S2 | Telegram bot notifications (stretch — skip if the sprint runs long) | done |

**Sprint exit check:** open the DEV bot from a phone, tap «Открыть content-scout», run the full flow inside Telegram, and share the bot handle with a second account.

## Sprint 7 — Single-blogger MVP: Mini App fix + competitor/results depth

**Goal:** per the 2026-07-21 reprioritization (single-blogger pilot focus), close out the live-blocking Mini App bug and round out the Результаты/Конкуренты screens with the data a solo blogger actually needs to judge a competitor's content: follower counts, comments, and a relative virality signal.

**Execution mode:** same as Sprint 6 — run stories back-to-back autonomously, in dependency order, no user intervention expected.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E8-S6 | Telegram Mini App auto-login bootstrap fix (critical) | done |
| 1 | E5-S4 | Subscriber count next to account name | done |
| 2 | E2-S3 | Competitor profile enrichment (depends on E5-S4) | done |
| 3 | E5-S3 | Comments count column | done |
| 4 | E5-S5 | Virality score per publication (depends on E5-S4) | done |

**Sprint 7 complete.** All 5 stories from the 2026-07-21 single-blogger reprioritization shipped and CI-green (a real CI failure surfaced two bugs — a Postgres `percentile_cont`/window-function incompatibility in E5-S5, and a test-session isolation bug in E2-S3's background worker job — both fixed same-day, see their BACKLOG.md Changelog entries). Every story's DEV smoke test is still deferred (consistent with this project's established pattern — Apify/Telegram-dependent verification always waits for a real device/account); a real-device + DEV pass over all of them is still owed, tracked as a standing carry-over rather than a blocking gate.

**Also shipped in the Sprint 7 window, untracked at the time, now backfilled as stories (see DONE.md):** E12-S3 (mobile results controls consolidation — single icon row, virality badge recolor, new virality/engagement/comments sort options, export sheet copy) and E3-S7 (run scope: last-N-publications mode, alongside the existing day-window scope).

## Sprint 8 — Navigation restructure: Details, Results, Analysis (locked 2026-07-22)

**Goal:** per the 2026-07-22 execution-plan session, extend the MVP with a reshaped project IA — bottom nav collapses to three tabs (Детали/Результаты/Анализ), Детали becomes a real dashboard (KPIs, competitor/scheduled-run links, run-history cards, create-run entry), opening a run gets its own Summary+Publications detail view, and Анализ ships as a teaser for future paid deep-analysis products. This sprint reshapes the IA that Sprint 9 (scheduled runs) and Sprint 10 (monetization) both build their entry points on top of.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E13-S1 | Bottom nav restructure: Детали / Результаты / Анализ | done |
| 1 | E13-S2 | Details dashboard: KPI card, nav links, run-history cards, create-run entry | done |
| 2 | E13-S3 | Competitors page trim | done |
| 3 | E16-S1 | Analysis teaser page | done |
| 4 | E15-S1 | Run-level AI summary generation | done |
| 5 | E15-S2 | Top-5-posts-by-virality for a run | done |
| 6 | E15-S3 | Run detail page: Summary + Publications tabs | done |

**E13 epic complete (2026-07-22 session):** all three nav-restructure stories (E13-S1/S2/S3) shipped back-to-back per explicit user request, scoped to E13 only. All three E13 stories' DEV smoke tests are deferred (no local Postgres/DEV login in this sandbox), consistent with this project's established pattern; verified instead via temporary scratch preview routes with mock data, screenshotted and deleted before each commit.

**Sprint 8 complete (2026-07-22 session):** E16-S1 and E15-S1/S2/S3 shipped back-to-back in a follow-up session (explicit user request: "run epics E16 and E15 back to back"), closing out the sprint. E15-S1 added `AnalysisRun.summary_status`/`summary_text`/`summary_topics` (migration `a9b8c7d6e5f4`) and the `generate_run_summary` worker step; E15-S2 added `GET /runs/{run_id}/top-virality`; E15-S3 introduced the `/projects/[id]/runs/[runId]` route and, since neither prior story had exposed its data via the API, extended `RunOut` to surface E15-S1's fields. All four stories' DEV smoke tests are deferred, same established pattern — verified via ruff/mypy/tsc/eslint locally (CI is the authoritative gate for pytest, no local Postgres in this sandbox) plus temporary scratch preview routes (mocked `fetch` for E15-S3, since its page does live API calls rather than taking props), screenshotted and deleted before each commit. Sprint 9 (E14 scheduled runs) is next.

## Sprint 9 — Scheduled runs (locked 2026-07-22)

**Goal:** recurring analysis runs on a day-of-week + time schedule, notified to Telegram on completion. First use of arq's cron scheduling in this codebase — new infra, not just new UI.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E14-S1 | Scheduled runs: schema and migration | done |
| 1 | E14-S2 | Scheduled runs: CRUD API + arq cron dispatcher | done |
| 2 | E14-S3 | Scheduled Runs page (list + create/edit) | done |
| 3 | E14-S4 | Wire Run-now / Schedule choice into Details' create-run flow | done |
| 4 | E14-S5 | Telegram notification for scheduled-run completion | done |

**Sprint 9 complete (2026-07-22 session):** all 5 stories shipped back-to-back per explicit user request ("run epics E14 all stories back to back"). New `scheduled_runs` table + arq's first cron job (5-minute tick, timezone-aware via stdlib `zoneinfo`) fire recurring runs through the exact same `enqueue_run`/`process_run` path manual runs use — which is also why E14-S5 needed no production code at all, only a test proving it. Frontend: a new Scheduled Runs list/create/edit page, plus a Запустить-сейчас/Запланировать choice wired into the existing run-dialog. All 5 stories' DEV smoke tests are deferred, same established pattern (no local Postgres/Redis/DEV login in this sandbox) — verified via ruff/mypy/tsc/eslint locally (CI is the authoritative gate for pytest) plus temporary scratch preview routes with mocked `fetch`, screenshotted at desktop + 375px and deleted before each commit. This closes Sprint 9 and the E14 epic; Sprint 10 (E8-S3 monetization) is next, still locked behind this per the 2026-07-22 execution plan.

**Post-Sprint-9 fix, 2026-07-25 (E14-S6, direct user request, out of order):** first live feedback on scheduled runs (the E14 epic's every smoke test had been deferred) surfaced that completions never notified Telegram and that the one-row-per-weekday model didn't match how the user wanted to configure schedules. E14-S6 redesigned `ScheduledRun` to one row per schedule (`days_of_week: int[]`), added an explicit Once/Recurring `mode` and a per-schedule `notify_enabled` toggle (default off, independent of manual-run notifications), and fixed the mobile bottom nav's barely-visible active-tab state along the way. This session also discovered this sandbox now has a working local Postgres (contrary to the assumption in every earlier Sprint 6-9 entry) — the full backend suite (238 tests) ran and passed for the first time, and the new migration was verified with a real upgrade/downgrade/upgrade round-trip. See DONE.md's `[E14-S6]` entry and BACKLOG.md for full details. Sprint 10 (E8-S3 monetization) is still next.

**Post-Sprint-9 addition, 2026-07-25 (E17 epic, direct user request, out of order):** ran the entire E17 (Run Deep Analysis) epic — all 9 stories, E17-S1 through E17-S9 — back-to-back in one session, ahead of the still-nominally-next Sprint 10 (E8-S3 monetization), per explicit instruction ("run epic E17 Run Deep Analysis - all stories back-to-back"). Backend: `deep_analyses`/`deep_analysis_items` tables (migrations `c1d2e3f4a5b6`, `d2e3f4a5b6c7`), dual-vendor comment scraping (Apify `apidojo` primary / Bright Data fallback, D32), Haiku per-item extraction, Sonnet structured-tool-use synthesis (D33), the full `POST/GET .../deep-analyses` API, and thin-comment-coverage degrade + partial-refund pricing (E17-S9). Frontend: the Разбор запуска history/new-analysis flow and the Статистика/Рекомендации report page. New decision **D36** (client-side comment sort, since the AC's live-vendor spike couldn't run in this sandbox). Every story's DEV smoke test is deferred, same established pattern (no live Apify/Bright Data/DEV login in this sandbox) — verified instead via the full backend suite (281 passed, up from 253 at Sprint 9's close) plus `tsc --noEmit`/`next lint`/`next build` (no Browser-tool verification, per CLAUDE.md's explicit no-agent-UI-testing constraint). See DONE.md's `[E17-S1]` through `[E17-S9]` entries and BACKLOG.md for full details. Sprint 10 (E8-S3 monetization) is still next; E17's `deep_analysis_token_multiplier`/`deep_analysis_thin_coverage_multiplier` remain explicit D35 placeholders pending real DEV `usage_events`.

**Untracked addition, 2026-07-26 to 2026-07-28 (new epic E18, backfilled at `/sprint-review` time):** between E17's close and this review, 26 commits shipped a full navigation/redesign overhaul with **no story IDs, no BACKLOG.md entries, and no DONE.md handovers at the time** — this file's "Current sprint" note kept saying "Sprint 10 is next" the whole time. The `/sprint-review` skill's mandatory untracked-fix scan (`git log` since the last documented story) is what surfaced it. Backfilled as **E18 Run-Centric Navigation & Redesign** (5 stories, E18-S1..S5, all `Status: done`, real dates from commit history) per direct user request rather than left undocumented. Summary: home screen became a unified cross-project run feed with a FAB (E18-S1, **supersedes E13's whole tab-bar IA**), the run-creation dialog and scheduled-task cards were rebuilt to match (E18-S2/S3), the deep-analysis auto-chain gained failure visibility (E18-S4), and the Usage page was reworked around Balance with a buy-tokens CTA stub that anticipates Sprint 10's real entry point (E18-S5). See DONE.md's `[E18-S1]` through `[E18-S5]` entries and BACKLOG.md for full details. **Methodology gap this exposes:** nothing in the current workflow catches a multi-day, multi-commit redesign landing without a story ID — see this review's proposed methodology change below. Sprint 10 (E8-S3) is still next, and now has a real UI entry point waiting for it (E18-S5's stub CTA).

## Sprint 10 — Verification sweep + monetization (re-planned 2026-07-28 `/sprint-review`, trimmed same day)

**Goal:** first, close the remaining deferred-smoke-test gap with one real pass; then ship token monetization via Telegram Stars (D19). E18-S5 already built a buy-tokens CTA stub as this story's real UI entry point.

**Scope note (same day, 2026-07-28):** the smoke sweep was originally scoped to all 39+ deferred entries, but the user confirmed they'd already manually clicked through the entire live app while building E18 — that covers every general UI/navigation/rendering flow, now marked `PASSED` in DONE.md. E19-S1 is trimmed to ~13 remaining items that a normal click-through can't hit: forced faults (insufficient balance, malformed API response, cross-user isolation), cron-timing (scheduled runs actually firing + Telegram DM), security-guardrail edge cases (invite code, rate limits, XLSX injection), and a couple of direct-DB checks. One item is flagged priority: the Apify `apidojo`/Bright Data comment-scraping fallback is a **known real gap**, not just untested — this DEV account's Apify plan already rejects the actor and no Bright Data credentials are set.

**Note (2026-07-29): E8-S3 ran before E19-S1, out of this table's declared order.** The user invoked `/start-story E8-S3` directly; asked explicitly whether to proceed out of order or do E19-S1 first, they chose to proceed. E19-S1 (still `backlog`) remains the mandatory-first item for whoever picks up this sprint next.

**E8-S3 re-scoped again 2026-07-29 per D37 (supersedes D30):** ships as **pay-as-you-go token top-ups** (quick picks 1000/2000/5000 + custom, minimum 300, 1 токен = 1 ₽), not the recurring 1990₽/month subscription D30 had planned — a direct user redirect mid-story, before any code was written for the subscription version. See D37 and BACKLOG.md's `[E8-S3]` entry.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E19-S1 | DEV smoke-test sweep, trimmed (mandatory — do first) | backlog |
| 1 | E8-S3 | Telegram Stars token top-ups (re-scoped per D37 — pay-as-you-go, not subscription) | done |

**Sprint 10 complete (2026-07-31 `/sprint-review`):** E8-S3 done 2026-07-29 (out of the table's declared order — see note above). E19-S1 did **not** close this sprint; carried to Sprint 11 as mandatory-first, deprioritized by direct user choice a second time. Two unplanned items also landed and are backfilled in DONE.md/BACKLOG.md: **E17-S10** (deep-analysis job-cancellation bug fix, found via a real stuck DEV run and fixed same session) and **E8-S8** (2026-07-30 Mini App iOS 401 + auto-project hotfix cluster, backfilled this review). The same E17-S10 investigation also produced new backlog epic **E20 Performance & Scale** (E20-S1..S4), scoped into Sprint 11 below.

## Sprint 11 — Verification sweep (carried over) + performance & scale (planned 2026-07-31 `/sprint-review`)

**Goal:** finally close E19-S1 (now mandatory two sprints running), then address the performance/scale gaps E17-S10's investigation surfaced — deep-analysis speed, worker/DB capacity, and provider-quota guardrails superseding D11's original MVP-scale assumption.

**Deferred-smoke-test count at planning time: 18** (≥3 threshold) — confirms E19-S1 as non-negotiable first item, not just a carry-over courtesy.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E19-S1 | DEV smoke-test sweep, trimmed (mandatory — do first, carried from Sprint 10) | done |
| 1 | E20-S2 | Worker & DB capacity for concurrent load | done |
| 2 | E20-S3 | Baseline rate limiting & provider-quota guardrails (depends on E20-S2) | done |
| 3 | E20-S1 | Batch deep-analysis comment scraping (speed) | backlog |
| 4 | E8-S7 | Surface token purchases in the Balance ledger | backlog |

**Explicitly not scheduled:** E20-S4 (50→20 competitor cap) — still pending direct user confirmation of the product decision, not an effort/priority call. See BACKLOG.md's `[E20-S4]` entry.

**Human touchpoint:** E19-S1 is a hands-on DEV pass by design; E20-S1's speedup is directly observable by running a deep analysis and timing it.

**E19-S1 closed 2026-07-31.** User's live results resolved all 12 AC items (several with no code change needed, since existing CI tests already covered them — see BACKLOG.md's `[E19-S1]` Changelog/Handover for the full per-item breakdown). Two real findings came out of it, both logged as new decisions:
- **D39** (backfill): the invite-code registration gate has been dead since 2026-07-19 (commit `053cbe3` superseded E7-S4 same-day) — never documented at the time. E19-S1's corresponding AC item was rewritten and closed against the actual current behavior, not the stale one; `test_register_succeeds_without_invite_code` added.
- **D40** (new product direction): Review and Analysis are to become fully independent runs — Analysis gets its own Apify scraping pipeline, no longer auto-chains off a completed Review (undoing E18-S1). Scope is the full independent-pipeline version, bigger than a quick fix, and needs its own discussion first (how Apify is used, per-worker capacity) — opened as new epic **E21 (Standalone Analysis Pipeline)**, starting with a scoping-only story `E21-S1`, **not yet scheduled into a sprint** pending that discussion.
- Also opened **E8-S9** (Telegram completion DM should deep-link into the Mini App, not the system browser) from a live PROD finding.
- The one item the user wants to do later (E3-S6's 8+-account wall-time timing) was split into its own story **E19-S2** so E19-S1 itself could close — `E19-S2` is unassigned, pick up whenever.
- **Next in this sprint: E20-S2** (Worker & DB capacity), per the table above.

**Untracked addition, 2026-08-01→02 (new story E2-S4, backfilled 2026-08-02):** three live-blocking competitor-list bugs were reported and fixed directly in chat, out of this sprint's declared order and with no story ID until close — same "add-story after the fact" pattern as E17-S10/E8-S8 rather than left undocumented. Backfilled as **E2-S4** (Competitor deletion, picker staleness, and picker scroll fixes). Summary: competitor deletion now soft-deletes (`Account.archived_at`) instead of hard-deleting into an unhandled `IntegrityError`, the run-creation picker refetches its competitor list instead of trusting a stale page-load snapshot, and the picker's list box no longer gets crushed by flex-shrink (`shrink-0` on a nested `overflow-hidden` flex item — see BACKLOG.md's `[E2-S4]` Changelog for the full DevTools-driven root-cause trail). Also surfaced and documented a Railway build-cache gotcha (stuck image digest across deploys, worked around via an env-var cache bust) extending `[E17-S10]`'s existing `--path-as-root` deploy note. E20-S2 (Worker & DB capacity) is still next in this sprint's declared order.

**E21-S1 closed 2026-08-03 (scoping session, direct user request via `/start-story E21-S1`):** the standalone-Analysis scoping discussion D40 called for (still "not yet scheduled into a sprint" as of the last entry above) ran to completion, well beyond its original audit-only framing — see BACKLOG.md's `[E21-S1]` Handover for full findings. Headline results: verified live against Apify's actual Store pages (not assumed) that the `apidojo` comments actor has no profile-discovery and no comment-sort capability, and that `comment_scraper.py` has been sending a non-existent `resultsLimit` field to it — the per-post comment cap has likely never been server-side enforced (**D41**, fix folded into `[E20-S1]`, also drops the default cap 25→15 comments/post to stay inside the vendor's free tier). User signed off on the standalone-Analysis proposal (**D42**): own scrape, 20-competitor-per-run cap (separate from the account list's 50-cap), incremental per-item token charging replacing today's up-front lump sum. A general **D43** ("partial run results + disclaimer, charge only for work done") emerged from the same conversation and applies to Review too, not just Analysis. **New stories opened:** `[E21-S2]` (the actual pipeline implementation, high priority, not yet scheduled), `[E21-S3]` (Analysis publications tab, depends on E21-S2), `[E15-S4]` (Review run-detail partial-results + disclaimer display — a live, verified UI gap: `run.error_message` is already returned by the API but never rendered, and a `failed` run hides its already-committed partial data), `[E15-S5]` (Review results competitor drill-down modal, direct feature request). `[E20-S1]`'s scope grew (see D41) but stays where it was. 200-DAU worker/provider-capacity math was explicitly **not** produced this session — still blocked on real Apify/Anthropic account limits from the dashboards, same blocker `[E20-S3]` already documented; nothing new to unblock it here. AI-insights UX review was raised and explicitly deferred by the user ("let's separately review this") — no story opened. **E20-S2 (Worker & DB capacity) is still next in this sprint's declared order** — none of this session's output changes that.

**E20-S2 closed 2026-08-03 (`/start-story E20-S3` redirected here after a dependency check):** invoking `/start-story E20-S3` surfaced that its governor explicitly shouldn't be built against the 25-run ceiling until E20-S2's `memory_mbytes` pin landed (E20-S3's own Handover said so) — user confirmed doing E20-S2 first. Shipped all 4 AC items: `memory_mbytes=256` pinned on every Apify actor call, `WorkerSettings.max_jobs=5` (was arq's unset default of 10, which allowed up to 50 simultaneous Apify calls against the real 25-run ceiling), explicit DB pool sizing (`pool_size=10`/`max_overflow=10`, conservative pending a real Postgres `max_connections` check this session couldn't do — `DATABASE_URL` access was correctly blocked as credential access), and new D46 recording the `numReplicas: 1`-stays decision with revisit thresholds. Full suite 325 passed. Smoke test deferred to a real DEV pass (same established pattern). See DONE.md's `[E20-S2]` entry and BACKLOG.md for full details. **E20-S3 is next**, now buildable against a real 25-run ceiling.

**Same-day follow-up (2026-08-03): real Apify concurrency limit confirmed, then revised (D44).** User pulled their actual Apify console numbers — **25 concurrent Actor runs, flat**, 16 GB total Actor RAM. First read (from one comments-actor run at 256 MB) concluded RAM wasn't a competing constraint — but **revised same-day** after three more real app-triggered runs of the base `apify/instagram-scraper` actor showed unpinned memory allocation swinging 128 MB↔4096 MB with no correlation to workload size (actual usage stayed 55–92 MB throughout). Root cause: neither `platforms/instagram.py` nor `comment_scraper.py` sets the `apify-client` SDK's `memory_mbytes` parameter, so every call falls back to a non-deterministic platform default — at 4096 MB, only 4 concurrent runs would exhaust the RAM budget, well below the 25-run ceiling. Fix (pin `memory_mbytes=256` on every call) is now a concrete AC in `[E20-S2]`; `[E20-S3]`'s governor depends on that fix landing first before its 25-run cap is trustworthy. Also still stands: today's `max_jobs`(unset→10)×`scrape_concurrency`(5) config can already fire up to 50 simultaneous Apify calls under realistic multi-user overlap — already 2× the real ceiling, now compounded by the memory issue. Anthropic's RPM/TPM limits remain the one still-unconfirmed number blocking `[E20-S3]`'s governor.

**E20-S3 closed 2026-08-03 (same session as E20-S2, `/start-story E20-s3`):** built the governor E20-S2 unblocked. New `services/apify_governor.py` — a Redis sorted-set-backed global semaphore (`acquire_apify_slot`, atomic Lua check-and-add, stale-entry pruning for crashed-worker safety) caps simultaneous Apify actor calls at 25 (D44) across all three real call sites (`platforms/instagram.py` content/profile fetch, `comment_scraper.py`'s primary-vendor fetch). Per-user short-window rate limiting (default 5/min, distinct from E7-S4's daily quota) added to `POST /projects/{id}/runs` and deep-analysis creation, by extending E7-S4's `check_rate_limit` with an optional user-id `key` override instead of its IP-only default. The scheduled-run-burst AC closed with no new code — the governor plus arq's `max_jobs=5` (D46) already bound it, per the story's own either/or wording. New **D47**, superseding D11. Full suite 331 passed (up from 325); this session's sandbox turned out to have a working local Redis too (`redis-cli ping` → `PONG`, same discovery pattern as the earlier local-Postgres find), so the new tests exercise it directly rather than deferring. Pushed and deployed to DEV same session (CI green, `/health` confirmed); observing the governor under real concurrent load is still deferred (same established pattern). See DONE.md's `[E20-S3]` entry and BACKLOG.md for full details. **Next in this sprint: `[E20-S1]`** (batch deep-analysis comment scraping).

**Untracked fix, 2026-08-03 (direct user request, same session as E20-S3close): live DEV deep-analysis failure diagnosed and fixed.** User ran a real Analysis on DEV right after E20-S3's deploy; it failed with "Не удалось сформировать отчёт. Попробуйте запустить анализ ещё раз." Diagnosed via `railway logs --service worker` (Railway CLI, already authenticated in this sandbox) rather than DB access (still off-limits, same as E20-S2's precedent): confirmed the base scrape and comment scraping both actually worked (the scary "Free Plan" messages in Apify's own actor logs are informational — the account's Free Plan just silently caps `apidojo` calls at 10 comments/post instead of the configured 25, explaining the run card's "Комментарии: 100" = 10 posts × 10 capped comments), narrowing the failure to Sonnet synthesis. Found and fixed two real bugs along the way:
- **Synthesis `max_tokens` was hardcoded at 4096** (`deep_analysis_synthesis.py`) — very plausibly too small for `REPORT_TOOL`'s multi-array Russian-language schema at this run's item count, causing a truncated/absent `tool_use` block with no exception raised. Now `Settings.deep_analysis_synthesis_max_tokens` (default 8192), and the two silent fail-branches (`tool_use is None`, malformed `stats`/`recommendations`) now log `stop_reason` + a `logger.warning` — previously both returned via the exact same generic Russian message with zero diagnostic trace anywhere, DB row included no distinguishing detail either.
- **Root-caused why nothing showed up in the worker logs at all, including the pre-existing `logger.exception` call in `synthesize_report`'s except block**: neither `main.py` (api) nor `worker.py` ever configured Python's root logger. arq's own `logging.config.dictConfig` only wires up the `"arq"` namespace (confirmed by reading `arq/logs.py`/`arq/cli.py` directly), and uvicorn's default config has the same "own namespace only" shape — so every `logging.getLogger(__name__).warning/.exception(...)` call anywhere in `src/` was going nowhere on either service. Fixed with an explicit `logging.basicConfig(...)` in both `main.py` and `worker.py` — a systemic fix, not specific to this one incident; every future `logger.*` call in this codebase is now actually visible in Railway.
- New test `test_synthesize_report_truncated_response_marks_failed_and_logs_stop_reason` reproduces the exact incident shape (empty `content`, `stop_reason="max_tokens"`) and asserts the new log line fires. Full suite 332 passed. `ruff`/`ruff format --check`/`mypy src` clean.
- **Flagged for `/sprint-review` backfill** per CLAUDE.md's story-tracking discipline — this was diagnosed and fixed directly in chat, no story ID yet, same pattern as E2-S4/E8-S8/E17-S10.
- Not yet re-verified live on DEV that the actual truncation was the real cause (vs. some other rare Sonnet response shape) — next real Analysis run on DEV is the test; if it still fails, the new logging will show the actual `stop_reason`/content shape this time instead of nothing.

**Untracked fix, 2026-08-03 (same session, follow-up): content-scrape timeout headroom + run diagnostics.** A second real DEV run (3 accounts) confirmed the truncation fix held (this run's synthesis succeeded) and surfaced a new, separate finding via `railway logs`: one account's content fetch landed at 47/50 items right at the 180s Apify timeout, and its automatic retry only barely succeeded at 166s — 14s of margin. Bumped `apify_content_scrape_timeout_secs` 180s→240s. Also added the diagnostics this exact investigation kept needing and didn't have: `process_run` now logs each run's real scope (account count, `duration_days`, `item_limit`) at start, `InstagramPlatform._with_retries` logs each retry attempt instead of failing silently, and hitting the hardcoded 50-item scrape ceiling now logs a warning (a day-window run landing exactly at 50 may be silently truncating an account's real post count). Full suite 332 passed, CI green, deployed to DEV.

**2026-08-04, same investigation continued: second real Analysis run analyzed end-to-end using the new diagnostics, plus three direct product-change requests.** A 2-account, "last 10 publications each" Analysis run (15 real publications found) was traced precisely via the new `process_run` scope log (confirmed `item_limit=10`, matching what the user configured — the settings-visibility gap below is exactly why this took log-diving instead of being visible in the app) — 730s (12.2 min) deep-analysis job, ~10.6 min (87%) spent in `extract_deep_analysis_items`'s sequential comment-fetch loop (16 calls, one at a time, ~40s apart including per-call Apify container spin-up overhead) — the same E20-S1-relevant bottleneck confirmed a second time at a different scale, plus a discovery that `railway logs --since/--until` silently truncates/drops data on wide, high-volume windows (minute-by-minute re-queries recovered the missing calls) — worth remembering for any future log investigation in this project. Three concrete product-change requests came out of reviewing this run together, all shipped same session:
- **Telegram notification timing, fixed:** for `deep_analysis` runs, `notify_run_complete` fired right after the *base scrape* finished (confirmed live: 06:48:13 UTC, the exact same second `run_analysis` completed, 12 minutes before the real Analysis result existed) — a Review-shaped "done" DM for a run the user asked to Analyze. `process_run` now skips that notification for `run_type == "deep_analysis"` (stat_collection runs unaffected); a new `notify_deep_analysis_complete` (accounts/publications/comments/tokens, links to the Analysis report page) fires once `process_deep_analysis` actually finishes, success or failure; a new `_notify_base_scrape_only` fallback covers the case where the auto-chain never even starts (insufficient tokens / chaining error) so that run still gets exactly one notification, not zero.
- **Token charging redesigned, D48:** the flat `deep_analysis_token_multiplier` (15 tokens/item) was replaced with 1 token per publication + 1 token per comment, **reconciled to real usage** (`_reconcile_real_usage`, new) once extraction's real per-item comment counts are known — supersedes the old thin-coverage discount multiplier entirely (usage-based billing already charges less on thin coverage, no second multiplier needed). Root cause this fixes: two real runs both showed Apify's Free Plan silently capping every comment call at 10 results, so the old 15/item flat charge was billing for comment coverage the pipeline never actually delivered.
- **Run-settings visibility — existing story broadened, not duplicated:** `[E15-S5]` (previously accounts-only competitor drill-down) now also covers showing the run's scope (`duration_days`/`item_limit`) and applies to both the Review and Analysis result pages, not just Review — see its Handover for the direct throughline to this session's log-diving.
- **Scope-change note logged, not implemented:** the user described a materially different future Analysis entry flow (single account or single-post-URL, not up-to-20 multi-select) — flagged in `[E21-S2]`'s Handover as needing its own short scoping pass (E21-S1-style) before E21-S2 is picked up, since it changes that story's core AC, not just adds to it.
- Full suite 339 passed. `ruff`/`ruff format --check`/`mypy src` clean. All untracked (direct chat requests) — flagged for `/sprint-review` backfill, same pattern as this session's earlier fixes.

**Sprint 11 complete, closed at the 2026-08-04 `/sprint-review`.** Planned: E19-S1, E20-S2, E20-S3 (all done), E20-S1 and E8-S7 (both carried to Sprint 12). Unplanned but landed: E21-S1 (scoping, no code), E2-S4 (backfilled competitor-list bugfixes), and E17-S11 (new — backfills the three untracked `fix:` commits from 2026-08-03/04's deep-analysis pipeline investigation: synthesis truncation, root-logger visibility, timeout headroom, notification timing, and D48's usage-based token-charging redesign). Untracked-fix scan (`git log a9e7a66..HEAD`) found no untracked epic — the sprint's `feat:` commits both carry story IDs. Deferred-smoke-test count at review time: 6 genuinely open (of 7 `DEFERRED` entries in DONE.md; the 7th was already explicitly deprioritized) — triggers the ≥3 mandatory-sweep rule again, closed by new story **E19-S3**.

## Sprint 12 — Mandatory smoke sweep + deep-analysis speed + ledger visibility (planned 2026-08-04 `/sprint-review`, re-ordered same day by PBR)

**Goal:** originally, close the 6 deferred-smoke-test items Sprint 11 left open, then continue Sprint 11's carried-over performance/monetization work. **Re-ordered 2026-08-04 (PBR session, direct user request):** the user wants to release to paying customers ASAP and walked through 6 pre-launch gaps; four map to backlog stories (one — `[E21-S2]` — was sitting on exactly the scoping question the user just answered, resolved as **D49**), two are new. These now lead the sprint; the original mandatory-first item (`[E19-S3]`) and the two previously-next items (`[E20-S1]`, `[E8-S7]`) are pushed after, per explicit user choice on sequencing.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E21-S2 | Standalone Analysis pipeline: own scraping, single-account/post scope, incremental token charging (D49 unblocked it) | done |
| 1 | E3-S8 | Run-creation estimate: explain methodology + when balance is deducted (Review) | done |
| 2 | E15-S5 | Run results: settings + competitor drill-down modal (Review and Analysis) — bumped to high priority | done |
| 3 | E18-S6 | Notification drawer: show task type/time/status instead of stale project name | done |
| 4 | E22-S1 | Review Telegram completion message: condensed formatting + quantified summary (new epic E22) | done |
| 5 | E19-S3 | DEV smoke sweep for Sprint 11's deferred items (was mandatory-first, now resumes here — already `in-progress`, paused mid-way 2026-08-04 by user choice) | in-progress |
| 6 | E20-S1 | Batch deep-analysis comment scraping (expanded scope, D41) | done |
| 7 | E8-S7 | Surface token purchases in the Balance ledger | done |

**Item 6 of the PBR list, partially scoped 2026-08-04:** the user supplied an exact target Telegram-message format for **Review** completions, opened as `[E22-S1]` above (new epic **E22 Report & Notification Messaging**). Still open and **not yet a story**: the equivalent Analysis (Разбор) completion DM, and either run type's in-app report *page* structure — get the same level of concrete detail from the user for those before opening more E22 stories.

**Explicitly not scheduled:** E20-S4 (50→20 competitor cap, pending product-decision confirmation — unrelated to E21-S2's now-resolved 1-account-or-post cap, D49 is Analysis-specific and doesn't touch the account list's own 50-cap, D13).

**Human touchpoint:** E19-S3 is a hands-on DEV pass by design; E20-S1's speedup is directly timeable by running a deep analysis before/after; E21-S2/E3-S8/E15-S5/E18-S6 all benefit from a real DEV click-through once shipped (this project's established deferred-smoke-test pattern still applies).

**Untracked fix, 2026-08-04 (Sprint 12 start): synthesis retry on malformed tool_use output.** First real DEV run after the previous session's notification-timing/D48 fixes hit a new, distinct failure — `Не удалось сформировать отчёт`. Root-caused via `railway logs`: the Sonnet synthesis call completed normally (`stop_reason=tool_use`, not `max_tokens` — the earlier truncation fix held) but the model's tool-call arguments contained only a `recommendations` key, omitting the required `stats` key entirely, despite `tool_choice` forcing the `submit_deep_analysis_report` tool. Confirmed as a new failure mode, not a recurrence: `tool_choice` guarantees a tool call happens, not that its arguments satisfy the schema's `required` list. Fix: `synthesize_report` now retries the Sonnet call once (`_MAX_SYNTHESIS_ATTEMPTS = 2`) when the tool_use output is missing or fails to include both `stats` and `recommendations`, before failing the analysis; every attempt is recorded as its own `usage_events` row (each is a real billed Anthropic call regardless of whether it parses). Also reconfirmed live: the notification-timing fix from the prior session worked correctly (Telegram DM fired right after `run_deep_analysis` completed, not after the base scrape). Full suite 340 passed (added 1), `ruff`/`ruff format --check`/`mypy src` clean. Untracked (direct chat request) — flagged for `/sprint-review` backfill.

**E19-S3 partially closed, 2026-08-04 (`/start-story E19-S3`):** 2 of 6 AC items confirmed live on DEV (E20-S2's memory pin + queueing behavior, E8-S8's new-account iOS flow) — both DONE.md entries updated `DEFERRED`→`PASSED`. The remaining 4 items (E20-S3 concurrency-governor load test, E17-S10 forced job-timeout, E8-S3 real Stars purchase, E4-S3 cost-optimization comparison) need live DEV interaction the user wasn't sure how to exercise; **by direct user choice, verification is paused here and picked back up after Sprint 12 closes** rather than continuing now. `[E19-S3]` stays `in-progress`, not split or closed. **Proceeding to `[E20-S1]` next**, per Sprint 12's declared order.

**`[E21-S2]` closed, 2026-08-04 (`/start-story E21-S2`, delivered end-to-end same session per direct user request, no intermediate check-ins).** Full implementation per D50/D49, then three further rounds of fixes driven entirely by the user's own DEV smoke test (each round: user reports a live issue → root-caused via `railway logs`/code reading → fixed → 350-test suite + ruff/mypy/tsc/eslint/build → pushed → DEV health-checked): (1) synthesis dropping the required `stats` object on thin single-post data, plus a `/me/usage` phantom double-line bug found while investigating; (2) a real comments-charged-vs-analyzed overcharge bug, found while chasing why `comments_limit=25` only yielded 10 analyzed comments — root cause turned out to be the Apify account's Free Plan silently capping that actor at 10 items, an account-level limitation promoted to new story `[E20-S5]`, not fixable in code; (3) UI polish (mode-picker screen restyle, comments_limit teaser chips) per direct feedback after the above were confirmed working. Full blow-by-blow in BACKLOG.md's `[E21-S2]` Changelog. **Proceeding to `[E3-S8]` next**, per Sprint 12's declared order (row 1).

**`[E3-S8]` closed, 2026-08-04 (`/start-story E3-S8`).** Small copy-only story: real component turned out to be `frontend/components/run-dialog.tsx`, not the guessed `app/(app)/projects/[id]/run-dialog.tsx` (confirmed dead/orphaned, no imports — pre-E18 leftover, not touched). Added a short RU explanatory line beneath the Review cost estimate; per the AC's own requirement, verified the actual `token_balance` debit timing in `worker.py` before finalizing copy — it's incremental (1 token/publication, per batch, during `summarizing`), not a single "after completion" event as the story's draft copy assumed, so the shipped copy describes that instead. `tsc --noEmit`/`eslint` clean; no tests needed (pure copy, per CONVENTIONS.md's frontend test bar); smoke test deferred per CLAUDE.md's no-agent-UI-testing constraint. ⚠️ This brings DONE.md's outstanding deferred-smoke-test count to 6 (≥5 threshold) — already covered by the in-progress `[E19-S3]` later in this sprint, not a new sweep. **Proceeding to `[E15-S5]` next**, per Sprint 12's declared order (row 2).

**`[E15-S5]` closed, 2026-08-04 (autonomous back-to-back pass through Sprint 12, direct user request — "complete the rest of sprint 12 stories back to back without my involvement," user doing smoke testing at sprint end).** Both AC halves resolved: scope (`duration_days`/`item_limit`/`analysis_mode`) was already on `RunOut`, no new field needed; the account list needed one new endpoint, `GET /runs/{run_id}/accounts`, reused by both the Review run-detail page and the Analysis report page (the latter already resolves its underlying `RunResponse` via `analysis.run_id`) rather than duplicating it per run type. New shared `frontend/components/run-settings-sheet.tsx` renders the read-only sheet on both pages behind a new settings-gear icon on the summary card. 354 backend tests passed (up from 350), ruff/mypy/tsc/eslint/`next build` all clean. Smoke test deferred (no-agent-UI-testing constraint) — brings the outstanding deferred count to 7, still covered by the already-open `[E19-S3]`, not a new sweep. **Proceeding to `[E18-S6]` next**, per Sprint 12's declared order (row 3); `[E19-S3]` (row 5) stays skipped in this pass — it's a hands-on DEV story paused mid-way by the user's own explicit choice, not something a headless session can resume.

**`[E18-S6]` closed, 2026-08-04 (same autonomous pass).** Pure `layout.tsx` render fix — `tracked.run` already carried everything the drawer needed (`run_type`/`created_at`/`started_at`), so no hook or backend change. Tracked-run rows now read type · time instead of the stale repeated project name; schedule-alert rows now lead with the already-descriptive skip-reason message (checked first, per the AC, that schedules don't need project framing post-D38 — confirmed, neither the Scheduled Runs page nor the home feed shows it either) plus the skip timestamp. `tsc`/`eslint`/`next build` clean, no backend/tests touched. **Proceeding to `[E22-S1]` next**, per Sprint 12's declared order (row 4).

**`[E22-S1]` closed, 2026-08-04 (same autonomous pass).** Shipped the user's exact target Telegram format for Review completions: bulleted stat lines, bold section headers, no bullet on top-item lines, a new "Потрачено токенов" line, and a disambiguated «Ревью»-labeled header. The AC's own "verify, don't assume" instruction on `progress_items` paid off — it's genuinely the wrong field (never adjusted down after a mid-run token-exhaustion truncation), fixed to use `progress_summarized` instead, a real bug caught before it shipped. `run_summary.py`'s prompt gained a ТЕГИ tagging block for real per-topic counts (server-aggregated, not model-trusted) and a deterministic per-format fact line, fully backward compatible with the pre-existing prompt shape. 362 backend tests passed (up from 354), ruff/mypy clean; no frontend changes needed (confirmed `runs/[runId]/page.tsx` already renders the richer text as-is). **Proceeding to `[E20-S1]` next**, per Sprint 12's declared order (row 7) — row 5 (`[E19-S3]`) stays skipped, same reasoning as before (hands-on DEV story, paused by explicit user choice, not resumable headlessly).

**`[E20-S1]` closed, 2026-08-04 (same autonomous pass).** Replaced the sequential per-post comment-fetch loop (the exact bottleneck a real DEV run earlier this sprint measured at ~87% of total wall time) with one batched Apify call per DB batch. Verified live via WebFetch that the actor's `maxItems` is a whole-run cap, not per-post, so batches request `len(posts) × per_post_limit` and rely on the existing `_sort_and_cap` after grouping. The one piece genuinely unverifiable in this sandbox — which field identifies a comment's source post in a multi-URL batch response — is handled defensively (a short candidate list, all-unmatched aborts the batch back to the safe per-item path) rather than guessed blind, and flagged clearly for the first live DEV run to confirm. Also folded in D41's `resultsLimit`→`maxItems` bug fix (both the new batched path and the pre-existing single-post one) and the 25→15 comments-per-post default drop. 368 backend tests passed (up from 362), ruff/mypy clean. **Sprint 12's declared order is now exhausted except `[E19-S3]`** (skipped throughout this pass, hands-on-DEV) **and `[E8-S7]`, next.**

**`[E8-S7]` closed, 2026-08-04 (same autonomous pass, last in Sprint 12's declared order besides `[E19-S3]`).** Extended `GET /me/runs` with `kind="purchase"` rows from `TokenPurchase`, interleaved chronologically with runs/deep-analyses in the same list (no separate endpoint or merge step needed) — closes the «Пополнения» filter's standing empty state from E18-S5. `tokens_charged` doubles as "credited" for purchase rows, disambiguated by `kind` on the frontend (positive/`text-success` vs. the existing negative/`text-ink`); `spentThisPeriod` explicitly excludes purchase rows so a top-up can't inflate it. 371 backend tests passed (up from 368), ruff/mypy clean, frontend build clean.

**Sprint 12's autonomous back-to-back pass complete, 2026-08-04 (direct user request — "complete the rest of sprint 12 stories back to back without my involvement," user doing smoke testing at sprint end).** Every row in the sprint's declared order shipped except `[E19-S3]` (row 5), which stays `in-progress` exactly where the user left it earlier this same day — it's a hands-on DEV pass by its own nature (4 of 6 AC items need live interaction the user wasn't sure how to exercise yet) and was explicitly paused by the user's own choice, not something a headless session can pick up. Five stories shipped this pass: `[E15-S5]`, `[E18-S6]`, `[E22-S1]`, `[E20-S1]`, `[E8-S7]` — each committed and pushed individually (CI green on every one checked so far), full backend suite grew 350→371 across the pass, zero regressions. This is **not** a formal `/sprint-review` close — that ceremony (untracked-fix scan, deferred-smoke-test tally, next-sprint planning) is left for the user to run when they're ready, especially since it naturally follows their own DEV smoke-testing pass over everything shipped here. Deferred-smoke-test count is now well past every prior ≥3/≥5 threshold in this project's history (E15-S5, E18-S6 needs none since it's UI-render-only and unverifiable-live either way, E22-S1, E20-S1, E8-S7 all DEFERRED) — expect the next `/sprint-review` to flag a mandatory sweep same as E19-S1/E19-S3 did.

**Post-Sprint-12, same day (2026-08-04): two real bugs found on the user's own first DEV smoke-test pass, fixed same session.**
1. **`[E15-S4]` closed** (already had a full BACKLOG.md story, unassigned/backlog, opened 2026-08-03 from D43) — the user hit exactly the gap it was scoped to close: a run that errored (started 15:23) charged −11 tokens on the Balance page but showed zero results on its own detail page. Fixed per the story's existing AC; also found and fixed a real backend gap the AC's own "confirm during implementation" instruction anticipated — `items.py`/`export.py` both required `status == done` even for an explicitly-requested single `run_id`, not just the "all runs" aggregate view, so the frontend fix alone wouldn't have been enough. See DONE.md's `[E15-S4]` entry.
2. **Untracked fix (not yet a story — needs `/sprint-review` backfill, same pattern as E2-S4/E8-S8/E17-S10):** post-mode Analysis (a single-publication URL, D49) was silently adding the resolved post author to the user's real Конкуренты list/picker — confirmed live via a screenshot showing two such accounts polluting the run-creation picker. Root cause: `worker.py:_resolve_or_create_account` always created a real, visible `Account` row (needed for `ContentItem.account_id`'s non-nullable FK), with no way to distinguish "a real competitor" from "just resolved for one post's byline." Fixed with a new `Account.hidden` column (migration `e5f6a7b8c9d1`) — post-mode-created accounts are hidden by default, excluded from `GET /projects/{id}/accounts` (the picker), `resolve_target_accounts` (so a "whole list" Review/Analysis run never scrapes one), and the 50-per-list cap trigger (extends the same non-archived-only rescoping `a2b3c4d5e6f7` did). Explicitly re-adding the same handle via "Добавить конкурентов" un-hides the same row in place (mirrors the existing archived-account reactivation pattern) rather than erroring or creating a duplicate. 8 new/extended tests. **Note for the user:** this only stops *new* pollution — the two accounts already visible in the screenshot (`@spoontamer`, `@tomafatalieva`) were created before this fix and are not retroactively hidden; remove them via the existing competitor-removal UI if you don't want them listed (soft-delete, no history lost).

Both fixes: full suite 378 passed (up from 371 at Sprint 12's close), ruff/ruff format/mypy clean, frontend `tsc --noEmit`/`next lint`/`next build` clean. Both pushed and deployed to DEV same session. Smoke tests deferred (no-agent-UI-testing constraint) — the user's own live reports are what surfaced both, so a follow-up look at the same run/screenshot scenario is the natural confirmation.

**Two more real bugs found and fixed same day, 2026-08-04→05, plus a billing question that surfaced a real pricing gap.**
3. **`[E21-S5]` closed (D51)** — direct user question ("how much anthropic api costs do we incur with each review and analysis?") surfaced two confirmed findings: the deep-analysis synthesis call was billed internally at Haiku's rate instead of Sonnet's real ~3x-higher rate, and D50's incremental charging had zero charge for that same synthesis call at all — a thin Analysis run could cost more in real Anthropic spend than it collected. Both fixed: real Sonnet unit costs for the synthesis `usage_events` rows, plus a new flat base charge per Analysis run. See DONE.md's `[E21-S5]` entry.
4. **`[E22-S2]`/`[E3-S9]` closed** (two more untracked fixes, one shared commit, split into separate stories by feature area at this review) — the notify toggle was schedule-only, "run now" had no opt-out; now overarching. Separately, "last N publications" under-delivered when a profile had a pinned post (Apify's `resultsLimit` cap applied before pinned-post filtering) — fixed with a buffered fetch + real-date sort. A third report (no Telegram DM on a PROD run) was investigated via `railway logs`: PROD's `worker` service has never made a Telegram API call while `api` has succeeded repeatedly — root cause not confirmed (blocked from reading Railway env vars directly), diagnostic logging added so the next occurrence is immediately traceable. See DONE.md's `[E22-S2]`/`[E3-S9]` entries.

All three: full suite 385 passed (up from 378), ruff/mypy clean, frontend tsc/eslint/build clean. `[E21-S5]` deployed via `v0.8.0`; `[E22-S2]`/`[E3-S9]` via `v0.9.0`. Both tags green on DEV and PROD.

**`/sprint-review` backfill run 2026-08-05** (user request: "make the backfill as proposed"), covering every untracked commit since Sprint 11's `d9f5a7f` review: `[E17-S12]` (synthesis retry, Sprint 12 start), `[E21-S4]` (post-mode account hiding), `[E21-S5]` (D51 pricing), `[E22-S2]`/`[E3-S9]` (notify toggle + pinned-post fix) all got real BACKLOG.md stories and DONE.md entries this session, backdated to their actual completion dates above. **Recurring-bug cluster flagged, not yet scheduled:** `[E17-S12]`, `[E21-S4]`, and `[E21-S5]` are three separate, real bugs in the Analysis pipeline found within ~36 hours of `[E21-S2]` shipping — none caught by the test suite at the time, all found via a real DEV/PROD run or a direct user question. This is a similar shape to `[E17-S11]`'s own cluster one sprint earlier. Proposing a dedicated regression/hardening story (working title: **`E21-S6` Analysis-pipeline regression sweep** — audit the synthesis retry path, the hidden-account flow, and the pricing model together for gaps a single-bug-at-a-time fix wouldn't catch) for the next sprint; **not added to BACKLOG.md yet, pending the user's go-ahead** on scope/priority.

**First live-user feedback batch, 2026-08-07 (documentation only, no code changed).** The user shared four items of direct feedback from the app's first real outside users. Captured as new backlog stories via `/add-story`, all `Status: backlog`/`Sprint: unassigned` — none started:
- **`[E8-S10]`** — Mini App hardware/gesture back exits to the bot chat instead of navigating in-app; framed as investigate-first since it may be a hard Telegram platform constraint (`BackButton` API vs. OS-level back/swipe), not assumed fixable.
- **`[E18-S7]`** — the left menu / right notifications side drawers are 90% width with no in-drawer close/X, and on a light-theme phone their background color reads as continuous with Telegram's own native chrome bar, so the user's instinct to tap the "close" button hits Telegram's native X and exits the whole Mini App instead of the drawer — a real accidental-exit trap, not cosmetic.
- **`[E22-S3]`** — replaces the existing per-run notify toggle (`[E14-S6]`/`[E22-S2]`) with two global Settings-page toggles (Review, Analysis) covering every run of that type, present and future, **no per-run override** (explicit user decision, so a user with several active runs always has one place to turn a run type's notifications off). This is the concrete detail this file's Sprint 12 section had flagged as still missing before more `E22` stories could open — now unblocked.
- **`[E8-S9]`** (pre-existing story, not new) — user re-reported the same DM-opens-browser-and-re-auths issue this story already tracks, and guessed DEV already fixed it. Re-checked `telegram_notify.py` this session: still unimplemented on both DEV and PROD (plain `<a href>` anchor, no `web_app` button) — likely a mix-up with the separately-shipped `[E8-S6]` auto-login fix. No new story opened; a correction note was added to `[E8-S9]`'s own Handover instead.

**Backlog grooming, 2026-08-07 (same session, immediately after the feedback batch above).** Full open-backlog review (22 items: 21 `backlog` + `[E19-S3]` `in-progress`; the other 80 are `done`). Three decisions resolved directly with the user:
- **`[E21-S6]` formalized** (was a working-title proposal only since the 2026-08-05 review) — Analysis-pipeline regression sweep, auditing `[E17-S12]`/`[E21-S4]`/`[E21-S5]` together for the class of gap a single-bug-at-a-time fix wouldn't catch. User: "add it now, include in planning."
- **`[E20-S4]` (50→20 competitor cap) deprioritized, not decided either way** — user: real usage right now is a single competitor account, so the cap question doesn't matter yet. Left `backlog`/unassigned; revisit once real usage grows past single digits.
- **`[E20-S5]` (Apify 10-comment ceiling) split into two tracks** — Apify plan upgrade explicitly deferred until 5 external test users (beyond the 2 internal team users already using it) confirm product value; BrightData fallback approved to provision now, independent of that timing. The BrightData track's first AC item is a **human prerequisite** (the user creating a BrightData account and setting Railway credentials — account creation/payment is outside what an agent session can do), so it's not immediately codeable either, just no longer blocked on a decision.

## Sprint 13 — First-user feedback fixes + Analysis pipeline hardening (locked 2026-08-07 backlog grooming)

**Goal:** close out the four items from the app's first real outside-user feedback (notification settings, drawer UX, back-button behavior, DM deep-linking), then resume the carried-over `[E19-S3]` smoke sweep, then run the newly-approved `[E21-S6]` regression sweep over the Analysis pipeline's recent bug cluster.

**Stories (in order):**

| # | Story | Title | Priority | Status |
|---|---|---|---|---|
| 0 | E22-S3 | Global notify toggles on Settings, replacing per-run overrides | high | backlog |
| 1 | E18-S7 | Side drawers: close/X + Telegram-chrome color collision | medium | backlog |
| 2 | E8-S10 | Investigate Mini App hardware back/swipe exiting to bot chat | medium | backlog |
| 3 | E8-S9 | Telegram DM deep-link into Mini App instead of browser | medium | backlog |
| 4 | E19-S3 | Resume DEV smoke sweep (Sprint 11's deferred items) | high | in-progress (carried over) |
| 5 | E21-S6 | Analysis-pipeline regression sweep | high | backlog |

**Not scheduled:** `[E20-S4]` (deprioritized, no near-term usage pressure — real usage is single-competitor scale) and `[E20-S5]` (blocked on the user provisioning real BrightData credentials — a human step outside this session — before its remaining AC is workable).

**Order confirmed by direct user agreement ("agree") to the proposal above.** Proceeding to `[E22-S3]` first.

**Autonomous back-to-back pass started 2026-08-07 (direct user request: "start and complete sprint 13 without my involvement").**

**`[E22-S3]` closed, 2026-08-07.** Two global Settings toggles (Review/Analysis) replace the per-run/per-schedule notify field entirely, no per-run override, per the story's own explicit AC. New `User.notify_review_enabled`/`notify_analysis_enabled` (migration `a3b4c5d6e7f8`) + `PATCH /auth/me/notifications`; new `notify_enabled_for_run_type` helper consumed by all 4 `worker.py` notify call sites; old per-run request fields kept accepted-but-ignored, not removed. Per-run toggle UI fully removed (not hidden) from both run dialogs and the now-misleading per-schedule notify badges removed from the home feed and Scheduled Runs page. A real pre-existing test-isolation gap (3 `test_telegram_webapp.py` tests bypass the test DB) surfaced via the new migration, fixed practically (dev DB migrated too) without touching the isolation gap itself. 393 backend tests passed (up from 385), ruff/mypy clean, frontend tsc/eslint/build clean. Smoke test deferred, same established pattern. **Proceeding to `[E18-S7]` next**, per Sprint 13's declared order.

## Sprint plan (projection, adjust at each /sprint-review)

- **Sprint 2:** E2-S1, E2-S2, E3-S1 — projects, competitor lists, run lifecycle with mock data (done)
- **Sprint 3:** E3-S2, E4-S1, E4-S2 — real Apify scraping, Claude summaries, full pipeline (done)
- **Sprint 4:** E5-S1, E5-S2, E6-S1 — results table, XLSX export, shortlist (done)
- **Sprint 5:** E6-S2, E7-S1, E7-S2 — history, usage rollups, admin view → **usable MVP** (E7-S2 carried into Sprint 6)
- **Sprint 6:** hardening + cost + redesign + **Telegram test launch, no payments** (see above)
- **Sprint 7 (proposed, 2026-07-21 reprioritization — single-blogger MVP focus):** E8-S6 Telegram Mini App bootstrap fix (critical, live-blocking bug for the pilot — root cause fixed, pending real-device smoke test, see BACKLOG.md), E5-S4 subscriber count in results table, E2-S3 competitor profile enrichment (depends on E5-S4's `fetch_profile`), E5-S3 comments count column, E5-S5 virality score per publication (depends on E5-S4)
- **Sprint 8 (locked, 2026-07-22 execution plan):** E13-S1/S2/S3 (nav restructure: Детали/Результаты/Анализ, Details dashboard, Competitors trim), E16-S1 (Analysis teaser), E15-S1/S2/S3 (run detail: AI summary, top-5-by-virality, Summary+Publications tabs)
- **Sprint 9 (locked, 2026-07-22 execution plan):** E14-S1..S5 — scheduled runs (schema, CRUD + arq cron dispatcher, Scheduled Runs page, Run-now/Schedule wiring, Telegram notification)
- **Sprint 10 (re-planned 2026-07-28 `/sprint-review`):** E19-S1 (mandatory DEV smoke sweep, 39+ deferred tests including all of E18) first, then E8-S3 re-scoped — single 1990₽/mo → 2000-token subscription via Telegram Stars (D30)
- **"Sprint 11" (projection label reused — see actual `## Sprint 11` header above for what really carries this number):** this row originally projected E17-S1..S9 (Run Deep Analysis), proposed 2026-07-25 and completed out of order the same day (see the Post-Sprint-9 addition above) — it shipped years before its projected slot and never got its own numbered header, unlike E18 (also out-of-order, also header-less). The **actual** Sprint 11 (planned 2026-07-31 `/sprint-review`) is E19-S1 + E20-S1..S3 + E8-S7, per the header above.
- **Post-MVP (not yet ordered):** E3-S3/E3-S4 (run resume, two-phase cost confirmation), E3-S5 HikerAPI switch, E7-S3 pre-public-launch hardening, E8-S4 share-to-bot, E9 Public API, E10 Content Generation, E11 IG Connection/Publishing/Analytics (spike first) — see BACKLOG.md and docs/ARCHITECTURE.md § Roadmap beyond MVP
