from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./dev.db", alias="DATABASE_URL"
    )
    api_allowed_origins: str = Field(default="", alias="API_ALLOWED_ORIGINS")
    default_api_key: str | None = Field(default=None, alias="DEFAULT_API_KEY")
    disable_ratelimit: bool = Field(default=False, alias="BPSR_DISABLE_RATELIMIT")

    @property
    def allowed_origins(self) -> List[str]:
        if not self.api_allowed_origins:
            # Default: allow only localhost origins when API_ALLOWED_ORIGINS not set
            # In production, set API_ALLOWED_ORIGINS to restrict to specific domains
            return [
                "http://localhost",
                "http://127.0.0.1",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        return [origin.strip() for origin in self.api_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
