"""App configuration loaded from environment variables.

Tất cả config đều qua file này — không dùng os.environ trực tiếp.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings từ .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────
    environment: Literal["development", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    secret_key: str = "dev-secret-change-in-production"
    allowed_origins: str = "*"

    # ── Auth ─────────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:8000"

    # ── Payments ─────────────────────────────────────────────────
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    # ── Riot API ─────────────────────────────────────────────────
    riot_api_key: str = ""
    riot_regional_url: str = "https://sea.api.riotgames.com"
    riot_platform_url: str = "https://vn2.api.riotgames.com"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://metascope:metascope@localhost:5432/metascope"
    sync_database_url: str = "postgresql://metascope:metascope@localhost:5432/metascope"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_concurrency: int = 2

    # ── Rate Limiting (Riot API) ─────────────────────────────────
    rate_limit_per_second: int = 20
    rate_limit_per_2min: int = 100
    rate_limit_max_concurrent: int = 20
    rate_limit_retry_max: int = 3

    # ── Cache TTL (giây) ─────────────────────────────────────────
    cache_ttl_tier_list: int = 900
    cache_ttl_comp_list: int = 900
    cache_ttl_comp_detail: int = 3600
    cache_ttl_champion_stats: int = 3600
    cache_ttl_trait_stats: int = 3600
    cache_ttl_player: int = 1800
    cache_ttl_search: int = 300
    cache_ttl_leaderboard: int = 1800
    cache_ttl_patches: int = 21600
    cache_ttl_static_data: int = 21600
    cache_ttl_guides: int = 300
    cache_ttl_match_analysis: int = 86400
    cache_ttl_analysis_summary: int = 1800

    # ── Pagination ───────────────────────────────────────────────
    default_page_size: int = 20
    max_page_size: int = 100

    # ── Stats Calculation ────────────────────────────────────────
    min_sample_size: int = 100
    patch_decay_factor: float = 0.85
    tier_boundaries: str = "S:90,A:70,B:45,C:20,D:0"

    # ── TFT ──────────────────────────────────────────────────────
    tft_set_number: int = 13
    default_region: str = "vn2"
    collect_regions: str = "vn2"

    @property
    def collect_regions_list(self) -> list[str]:
        """Parse collect_regions string thành list."""
        return [r.strip() for r in self.collect_regions.split(",")]

    @property
    def origins_list(self) -> list[str]:
        """Parse allowed_origins string thành list."""
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def tier_boundaries_map(self) -> dict[str, int]:
        """Parse tier_boundaries thành dict. Ví dụ: {'S': 90, 'A': 70, ...}."""
        result = {}
        for item in self.tier_boundaries.split(","):
            tier, pct = item.split(":")
            result[tier.strip()] = int(pct.strip())
        return result

    @property
    def is_development(self) -> bool:
        """True nếu đang chạy trong môi trường development."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """True nếu đang chạy trong production."""
        return self.environment == "production"

    def validate_production(self) -> None:
        """Kiểm tra config bắt buộc cho production. Gọi khi startup."""
        if not self.is_production:
            return
        errors = []
        if not self.riot_api_key:
            errors.append("RIOT_API_KEY must be set")
        if self.secret_key == "dev-secret-change-in-production":
            errors.append("SECRET_KEY must be changed in production")
        if self.allowed_origins == "*":
            errors.append("ALLOWED_ORIGINS must not be '*' in production")
        if not self.redis_password:
            errors.append("REDIS_PASSWORD must be set in production")
        if errors:
            raise ValueError(f"Production config errors: {'; '.join(errors)}")


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance.

    Dùng @lru_cache để chỉ parse .env một lần.
    """
    return Settings()


# Singleton export — dùng trong toàn bộ app
settings = get_settings()
