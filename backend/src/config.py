from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://scout:scout@localhost:5432/content_scout"
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "local-dev-secret-do-not-use-in-prod"
    access_token_expire_minutes: int = 1440

    worker_job_timeout_secs: int = 3600
    scrape_concurrency: int = 5
    # E20-S2/D44: arq's max_jobs bounds total concurrent worker jobs across every function
    # (run_analysis, fetch_account_profile, run_deep_analysis) sharing one worker process. Each
    # run_analysis job can itself fire up to scrape_concurrency Apify calls at once, so the
    # worst case is worker_max_jobs * scrape_concurrency simultaneous Apify actor runs — sized
    # here so that worst case lands at the confirmed 25-concurrent-run ceiling (5 * 5 = 25), not
    # above it (the previous unset arq default of 10 allowed up to 50).
    worker_max_jobs: int = 5
    # D44: pin Apify actor memory allocation instead of trusting the platform's non-deterministic
    # per-run default (observed swinging 128-4096 MB on identical real workloads). 256 MB leaves
    # ~2.7x headroom over the highest actual usage observed (92.5 MB) across every sampled run.
    apify_actor_memory_mbytes: int = 256
    # E20-S2: explicit DB pool sizing instead of SQLAlchemy's unconfigured default (5 + 10 = 15).
    # Conservative pending real confirmation of the Railway Postgres plan's max_connections —
    # api and worker each run their own engine/pool (numReplicas=1 each), so the combined peak
    # is 2 * (db_pool_size + db_max_overflow) = 40 connections today.
    db_pool_size: int = 10
    db_max_overflow: int = 10

    registration_invite_code: str = ""
    max_runs_per_user_per_day: int = 10
    # E20-S3/D44: global ceiling on simultaneous Apify actor calls across the whole worker
    # fleet (not just one process) — arq's max_jobs/scrape_concurrency only bound concurrency
    # within a single worker process, not across fetch_account_profile/comment-scraping calls
    # firing alongside run_analysis jobs. Matches the confirmed 25-concurrent-Actor-run ceiling.
    apify_max_concurrent_actor_runs: int = 25
    # E20-S3: short-window per-user limiter on run-creation/deep-analysis-creation, distinct
    # from max_runs_per_user_per_day's daily cap — stops a scripted burst within one minute.
    write_endpoint_rate_limit_per_minute: int = 5

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""  # @handle without @; used by Login Widget
    telegram_webhook_secret: str = ""
    web_url: str = "http://localhost:3000"  # public frontend URL for bot deep links

    # E8-S3/D37: pay-as-you-go token top-ups via a one-time Telegram Stars invoice.
    # stars_per_token converts a token amount to a Stars invoice amount — placeholder pending
    # a real FX check (Stars can't invoice in RUB directly), same pattern as D35's multiplier.
    stars_per_token: float = 1.0
    min_token_purchase: int = 300

    use_mock_platform: bool = True
    apify_api_token: str = ""
    apify_ig_actor_id: str = ""
    # Was hardcoded at 180 in platforms/instagram.py — a live DEV run (2026-08-03/04) showed a
    # single account's content fetch land at 47/50 desired items right at the 180s cutoff,
    # forcing an automatic retry (services/instagram.py's own retry logic) that then barely
    # succeeded at 166s on the second attempt. 240s gives real headroom for large accounts
    # instead of relying on a lucky second try.
    apify_content_scrape_timeout_secs: int = 240
    # Apify's pay-per-event pricing auto-caps each run's `maxTotalChargeUsd` at the account's
    # entire remaining monthly balance when we don't set one ourselves. With 2+ runs in flight
    # those uncapped reservations can together exceed the real balance, and every run past the
    # first sits in READY forever (never actually starts) — the account isn't out of budget,
    # it's just double-booked. Cap it per account fetch (50 results * $0.0027/result ≈ $0.14).
    apify_max_charge_per_fetch_usd: float = 0.5

    anthropic_api_key: str = ""
    summary_model: str = "claude-haiku-4-5-20251001"
    summary_concurrency: int = 5
    summary_image_max_side: int = 512
    summary_skip_image_caption_chars: int = 200
    summary_batch_threshold: int = 20

    # E3-S1: mock platform only (InstagramPlatform lands in E3-S2). Estimate constants are
    # provisional and config-driven so real Apify/Claude pricing can be dropped in without a
    # code change (D26 spirit — never hardcode prices call sites care about).
    avg_items_per_account_per_day: float = 1.2
    apify_unit_cost_usd: float = 0.0027
    avg_claude_input_tokens_per_item: int = 350
    avg_claude_output_tokens_per_item: int = 80
    claude_input_token_cost_usd: float = 0.000001
    claude_output_token_cost_usd: float = 0.000005

    # E17/D48/D50: Run Deep Analysis token charging — 1 token per publication analyzed + 1
    # token per comment actually analyzed, charged incrementally as each item's real work
    # completes (see services/deep_analysis.py:charge_tokens_for_item). Also the account-mode
    # default per-post comment count; post mode's user-configurable comments_limit overrides it.
    # 15 (was 25, D34) per D41/E20-S1: matches apidojo's free-included tier exactly
    # (apify_comment_included_comments below), so the default run yields zero overage cost.
    deep_analysis_comments_per_post: int = 15  # D41

    # E17-S2: comment scraping, dual-vendor per D32. Primary actor's pricing has two
    # components — a flat post-query event, plus per-comment overage past the first
    # apify_comment_included_comments (15).
    apify_comments_actor_id: str = "apidojo/instagram-comments-scraper-api"
    apify_comment_query_cost_usd: float = 0.0075
    apify_comment_included_comments: int = 15
    apify_comment_overage_cost_usd: float = 0.0005
    brightdata_api_token: str = ""
    brightdata_api_base_url: str = "https://api.brightdata.com"
    brightdata_ig_comments_dataset_id: str = ""
    brightdata_comment_request_cost_usd: float = 0.00075

    # D51: Sonnet 5 is ~3x Haiku's per-token cost on both axes — the synthesis call below was
    # previously recorded in usage_events at the Haiku rates above, under-counting its real USD
    # cost. Priced at standard (non-intro) Sonnet 5 rates ($3/$15 per 1M) rather than the
    # $2/$10 intro rate that runs through 2026-08-31, so this constant doesn't go stale a few
    # weeks after being added.
    claude_sonnet_input_token_cost_usd: float = 0.000003
    claude_sonnet_output_token_cost_usd: float = 0.000015

    # D52: base token charge per Review run, covering the one run-level Claude summary call
    # (run_summary.py:generate_run_summary, Haiku) — the Review-side counterpart to D51's
    # Analysis base charge below, for the same reason: that call previously had zero token
    # charge attached to it anywhere, only the existing 1-token/publication per-item charge.
    # Charged once, only if a real response actually comes back from that call (not charged if
    # it raises before returning — no real Anthropic cost was incurred).
    review_base_charge_tokens: int = 5

    # D51: base token charge per Analysis run, covering the one fixed-cost Sonnet synthesis call
    # (D33/E17-S4) that D50's incremental per-item charging never accounted for — that call's
    # real cost doesn't shrink with fewer items, so a thin run (e.g. single-post mode) could
    # otherwise cost more in real Anthropic spend than the per-item charge collects. Charged
    # once, up front of the synthesis attempt (see deep_analysis_synthesis.py:synthesize_report),
    # distinct from charge_tokens_for_item's per-item/per-comment charges.
    deep_analysis_base_charge_tokens: int = 5

    # E17-S4: synthesis is the one non-Haiku call in the pipeline (D33).
    deep_analysis_synthesis_model: str = "claude-sonnet-5"
    # Was hardcoded at 4096 — a live DEV failure (2026-08-03) surfaced no other error signal
    # for a 10-item/100-comment run, and the REPORT_TOOL schema's required fields (multiple
    # arrays across stats+recommendations, all in Russian, which tokenizes less densely than
    # English) are plausibly enough to hit that ceiling mid-JSON, breaking the tool_use block.
    deep_analysis_synthesis_max_tokens: int = 8192

    # E17-S9: below this share of `done` items having any fetched comments, the report
    # degrades to content-layer-only (comment-derived sections stripped) — pricing no longer
    # needs a separate multiplier here (D48): real-usage billing already charges less on a
    # thin-coverage run, since fewer comments were actually analyzed.
    deep_analysis_comment_coverage_threshold: float = 0.5

    # E5-S5: self-relative virality badge thresholds (item's performance_ratio vs. that
    # account's own median in the run) — tunable without a code change, same pattern as the
    # estimator constants above.
    virality_high_ratio: float = 2.0
    virality_low_ratio: float = 0.7
    virality_min_items: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url_async(self) -> str:
        """Railway provides postgres:// DSNs; SQLAlchemy needs the asyncpg dialect prefix."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url.removeprefix(prefix)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
