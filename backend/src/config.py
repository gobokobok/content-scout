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

    # E3-S1: mock platform only (InstagramPlatform lands in E3-S2). Estimate constants are
    # provisional and config-driven so real Apify/Claude pricing can be dropped in without a
    # code change (D26 spirit — never hardcode prices call sites care about).
    avg_items_per_account_per_day: float = 1.2
    apify_unit_cost_usd: float = 0.01
    avg_claude_input_tokens_per_item: int = 350
    avg_claude_output_tokens_per_item: int = 80
    claude_input_token_cost_usd: float = 0.000001
    claude_output_token_cost_usd: float = 0.000005

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
