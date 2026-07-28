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

    registration_invite_code: str = ""
    max_runs_per_user_per_day: int = 10

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

    # E17: Run Deep Analysis paid add-on. deep_analysis_token_multiplier is an explicit
    # placeholder (D35) — the real value is set only after reading a real pilot run's
    # usage_events totals on DEV, since comment-scraping cost (D32/D34) doesn't scale like
    # the base run's flat per-item Apify rate a naive guess would assume.
    deep_analysis_token_multiplier: float = 15.0
    deep_analysis_comments_per_post: int = 25  # D34

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

    # E17-S4: synthesis is the one non-Haiku call in the pipeline (D33).
    deep_analysis_synthesis_model: str = "claude-sonnet-5"

    # E17-S9: below this share of `done` items having any fetched comments, the report
    # degrades to content-layer-only (comment-derived sections stripped) and the customer is
    # only charged deep_analysis_thin_coverage_multiplier of the full rate.
    deep_analysis_comment_coverage_threshold: float = 0.5
    deep_analysis_thin_coverage_multiplier: float = 0.5

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
