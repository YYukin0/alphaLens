from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DeepEquity"
    app_version: str = "0.2.0"
    debug: bool = False

    database_url: str = "postgresql://alphalens:alphalens@postgres:5432/alphalens"
    redis_url: str = "redis://redis:6379/0"

    sec_user_agent: str = "DeepEquity Research Platform contact@deepequity.local"
    sec_base_url: str = "https://data.sec.gov"
    sec_edgar_search_url: str = "https://www.sec.gov/cgi-bin/browse-edgar"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://frontend:5173",
    ]

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    filing_types: list[str] = ["8-K", "10-Q", "10-K"]
    max_filings_per_sync: int = 10
    historical_filing_years: int = 10
    default_filing_page_size: int = 25

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_max_content_chars: int = 15000
    auto_extract_events: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
