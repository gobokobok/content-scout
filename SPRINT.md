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
| 0 | E19-S1 | DEV smoke-test sweep, trimmed (mandatory — do first, carried from Sprint 10) | backlog |
| 1 | E20-S2 | Worker & DB capacity for concurrent load | backlog |
| 2 | E20-S3 | Baseline rate limiting & provider-quota guardrails (depends on E20-S2) | backlog |
| 3 | E20-S1 | Batch deep-analysis comment scraping (speed) | backlog |
| 4 | E8-S7 | Surface token purchases in the Balance ledger | backlog |

**Explicitly not scheduled:** E20-S4 (50→20 competitor cap) — still pending direct user confirmation of the product decision, not an effort/priority call. See BACKLOG.md's `[E20-S4]` entry.

**Human touchpoint:** E19-S1 is a hands-on DEV pass by design; E20-S1's speedup is directly observable by running a deep analysis and timing it.

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
