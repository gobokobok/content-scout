# ARCHITECTURE — content-scout

## System overview

```
┌─────────────┐     HTTPS      ┌─────────────┐            ┌────────────┐
│  Next.js 15 │ ─────────────▶ │   FastAPI   │ ──────────▶│ PostgreSQL │
│  (ru UI)    │   REST/JSON    │   (api)     │ SQLAlchemy └────────────┘
└─────────────┘                └──────┬──────┘                  ▲
                                enqueue│ (arq)                  │
                               ┌───────▼──────┐                 │
                               │    Redis     │                 │
                               └───────┬──────┘                 │
                               ┌───────▼──────┐    writes items,│usage
                               │    Worker    │─────────────────┘
                               │  (arq jobs)  │
                               ├──────────────┤
                               │ Apify client │→ IG scraping (per account)
                               │ Claude client│→ Haiku summaries (caption+cover)
                               └──────────────┘
```

Two Railway services per environment (api + worker share the backend image, different start commands) plus the frontend service, Postgres and Redis plugins.

## Domain model

```
users ──1:N── workspace_members ──N:1── workspaces
users ──1:1 (MVP)── workspaces (personal, auto-created at signup)
workspaces ──1:N── projects
projects ──1:N── account_lists          (one per platform: instagram | youtube | tiktok | threads)
account_lists ──1:N── accounts          (≤50 per list; normalized_url unique within list)
projects ──1:N── analysis_runs
analysis_runs ──1:N── content_items
projects ──1:N── shortlist_items ──N:1── content_items
users/analysis_runs ──1:N── usage_events
```

### Key tables

**users** — id, email (unique), password_hash, is_admin, created_at
**workspaces** — id, name, kind (`personal` | `team`), created_at
**workspace_members** — workspace_id, user_id, role (`owner` for MVP)
**projects** — id, workspace_id, name, archived_at, created_at
**account_lists** — id, project_id, platform (enum), created_at; unique (project_id, platform)
**accounts** — id, account_list_id, input_url, normalized_url, handle, status (`active` | `failed`), fail_reason, created_at
**analysis_runs** — id, project_id, requested_by, duration_days (1–7), status (`pending` | `scraping` | `summarizing` | `done` | `failed`), progress_accounts, progress_items, error_message, estimated_cost_usd, total_cost_usd, total_input_tokens, total_output_tokens, started_at, finished_at
**content_items** — id, run_id, account_id, external_id, type (`reel` | `post` | `carousel` | future: `video` | `short`), published_at, title, url, cover_url, caption, summary, likes, views (nullable — see D14), comments, raw (JSONB)
**shortlist_items** — id, project_id, content_item_id, added_by, added_at, removed_at (soft delete → history); unique active (project_id, content_item_id)
**usage_events** — id, user_id, run_id, kind (`apify_result` | `claude_input_tokens` | `claude_output_tokens`), quantity, unit_cost_usd, created_at

Derived metrics (`days_since_published`, `views_per_day`, `likes_per_day`) are computed in SQL at read time from `published_at` and now() — always fresh, no staleness, sortable server-side. `views_per_day` is NULL when views is NULL.

## Analysis run lifecycle

1. UI: user picks duration (1–7 days) → `POST /runs/estimate` → shows estimated cost → user confirms (D10)
2. `POST /runs` creates row `pending`, enqueues arq job, returns run id
3. Worker `scraping`: for each account (bounded concurrency), `Platform.fetch_content(account, since)` → normalize → insert content_items → write `apify_result` usage_events; per-account failure marks the account failed, run continues
4. Worker `summarizing`: batch items through summarizer (caption + cover → Haiku) → write summaries + token usage_events; per-item failure gets fallback text
5. `done` (or `failed` with error_message); totals rolled up onto the run
6. Frontend polls `GET /runs/{id}` (2s interval) for status + progress

## Platform abstraction

```python
class Platform(Protocol):
    slug: str  # "instagram"
    def normalize_url(self, raw: str) -> NormalizedAccount: ...
    async def fetch_content(self, account: Account, since: datetime) -> list[RawContentItem]: ...
```

Implementations: `platforms/mock.py` (fixtures, gated by USE_MOCK_PLATFORM), `platforms/instagram.py` (Apify). YouTube/TikTok/Threads are future implementations; nothing outside `platforms/` may import the Apify client.

## Auth

Email+password (bcrypt) → JWT access token (HS256). Auth logic behind `AuthProvider` interface so VK ID / SMS providers can be added post-MVP (D4). Registration creates user + personal workspace + owner membership in one transaction. All API routes except `/auth/*` and `/health` require a valid token; resources are always scoped through workspace membership (foreign ids → 404).

## Usage metering (monetization-ready)

Every external cost writes a `usage_events` row at the moment it is incurred (D12): one per Apify result fetched, one per Claude call for input and output tokens (quantity = tokens). `unit_cost_usd` is captured at write time from config so historical costs survive price changes. Monetization later = pricing rules over already-collected events; nothing to retrofit.

## i18n

next-intl, single `ru` locale, all strings in `frontend/messages/ru.json`. Backend errors return `{code, message_ru}`. Adding English later = one new messages file + locale switch.

## Non-goals (MVP)

Script generation, VK ID/SMS auth, other platforms, billing, team workspaces, video transcription, webhooks/notifications.

## Roadmap beyond MVP

### Telegram Mini App (D17–D19)

No native app planned. The mobile story is: the same Next.js frontend (already mobile-first per D16) runs unmodified inside Telegram as a **Mini App** (`t.me/ContentScoutBot`). Delivery order (E8):

1. **Telegram Login** — new `AuthProvider` implementation (D18) alongside email+password, ahead of the still-deferred VK ID.
2. **Bot notifications** — link TG account in settings; worker (or a lightweight notifier consuming run-completion events) sends "Анализ готов ✅" with a deep link back into the run.
3. **Mini App + Telegram Stars** — frontend wrapped with the Telegram Web App SDK; auth via signed `initData` (no login form inside Telegram); subscription plans and pay-per-run priced in Stars, layered on top of the existing `usage_events` ledger (a plan = N included usage units before Stars are charged).

The Mini App still loads the same origin as the web app, so it inherits whatever stage of the RU-reachability plan (below) is active — Telegram does not shield or proxy your domain.

### Russian network reachability (D20)

Staged, infra-only — no application code changes required at any stage, because scraping/LLM calls already live only in the `worker`:

1. **Pilots (now):** no change. Users have VPNs; Railway domains (`*.up.railway.app`) are reachable.
2. **Public RU launch:** register a custom domain; front Railway with a RU-hosted reverse proxy (small VPS on Timeweb/Selectel running Caddy/nginx, or a RU CDN) so RKN sees a Russian-serving IP for the domain while Railway stays the origin.
3. **Monetization/scale:** move `web` + `api` + Postgres to RU cloud (Timeweb Cloud, Amvera, or Yandex Cloud) for 242-ФЗ data-localization compliance and RU payment-processor integration; **keep the `worker` running abroad** (Railway or an EU VPS) since it's the only component that calls Apify and Anthropic — both unreliable or unavailable from RU infrastructure/billing. Bridge the split via WireGuard/Tailscale, or by having the worker pull jobs through the public API instead of touching the RU-local DB directly.

### Content generation & publishing (E10–E11, D23–D24)

The shortlist is the input to a generation pipeline: **script → assets → review → delivery**. Three content types (D23): пост (photo + text, default), карусель (hero + slides + text; optional background music auto-renders it as a reels video), reels (blogger assets + script text overlays). Each generation request is an independent worker job — parallel, non-blocking, metered in usage_events, TG-notified on completion. Asset production sits behind a `ContentEngine` interface so it can run internally or be delegated per-niche to a football-content-engine-style external service through the D21 API/webhook contract.

Delivery default is **download** (zip of media + caption). Direct publishing to Instagram exists only via the official Graph API (D24): blogger's Business/Creator account, OAuth per project (a project models one own account), one-time Meta app review for the SaaS — feasibility spike E11-S1 before any build. No private-API automation ever: blogger account bans are an unacceptable product risk. The same Graph API connection later powers own-account analytics (E11-S3), which is also a plausible standalone product.

### Public API & engine integration (D21)

Workspaces, projects, runs, and shortlist_items already have durable IDs and are exposed as REST resources — the API-first shape of E1–E7 is what makes this cheap later. Post-MVP (E9): scoped API tokens per workspace, and webhooks (`run.completed`, `shortlist.updated`, later `script.ready`) so a downstream content-generation product (in the shape of football-content-engine) can subscribe to a scout project's shortlist and pull items/scripts without any shared codebase — a contract between two products, not a merge.
