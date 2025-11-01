from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./dev.db", alias="DATABASE_URL"
    )
    api_allowed_origins: str = Field(default="", alias="API_ALLOWED_ORIGINS")
    default_api_key: str | None = Field(default=None, alias="DEFAULT_API_KEY")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    status_cache_seconds: int = Field(default=15, alias="STATUS_CACHE_SECONDS")

    @property
    def allowed_origins(self) -> List[str]:
        if not self.api_allowed_origins:
            return []
        return [origin.strip() for origin in self.api_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
