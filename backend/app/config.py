"""Environment configuration and settings.

All secrets/config come from environment variables (.env in local dev).
Never hardcode API keys here.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://jobless:jobless@localhost:5432/jobless"

    # LLM provider (OpenRouter, OpenAI-compatible API)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_site_url: str = ""
    openrouter_app_name: str = "jobless"

    # Embeddings
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Matching thresholds
    stage1_similarity_threshold: float = 0.35
    stage2_min_score: int = 50

    # Source adapters
    agency_api_base_url: str = ""
    agency_api_key: str = ""
    aggregator_api_base_url: str = "https://api.adzuna.com/v1/api"
    aggregator_app_id: str = ""
    aggregator_app_key: str = ""
    ats_boards_greenhouse_slugs: str = ""  # comma-separated company board tokens
    ats_boards_lever_slugs: str = ""  # comma-separated company slugs

    # Scheduler
    collection_interval_minutes: int = 60

    # Dedup
    dedup_fuzzy_threshold: int = 90  # rapidfuzz score 0-100

    # Auth (single-user app for now)
    session_secret: str = "dev-secret-change-me"

    # Document output
    generated_docs_dir: str = "./generated_docs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
