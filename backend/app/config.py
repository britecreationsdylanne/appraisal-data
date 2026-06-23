from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config. Loaded from backend/.env (falls back to sane local defaults)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "local" runs the synthetic demo (creates/seeds tables). "production" treats the
    # appraisal DB as READ-ONLY: no create/alter/seed against it ever.
    app_env: str = "local"

    # The appraisal database. READ-ONLY in production (real appraisal data).
    database_url: str = (
        "postgresql+psycopg2://appraisal:appraisal@localhost:5436/appraisal_research"
    )

    # The app's own read/write database (saved templates, history, saved items).
    # Separate instance in production; falls back to `database_url` locally.
    app_database_url: str = ""

    anthropic_api_key: str = ""

    # Model tiers (model-migration: frontier / standard / economy)
    model_frontier: str = "claude-fable-5"
    model_standard: str = "claude-sonnet-4-6"
    model_economy: str = "claude-haiku-4-5-20251001"

    # Decorative/editorial image generation (hero shots, backgrounds — NOT data charts).
    # Data charts are always rendered deterministically. Leave blank to disable.
    openai_api_key: str = ""
    model_image: str = "gpt-image-2"

    seed_rows: int = 60000
    seed_start_year: int = 2019
    seed_end_year: int = 2025

    @property
    def souls_live(self) -> bool:
        """True when a real Anthropic key is present; otherwise souls run deterministic."""
        return bool(self.anthropic_api_key.strip())

    @property
    def is_local(self) -> bool:
        """Local/dev mode — safe to create + seed the synthetic appraisal tables.
        In production this is False and the appraisal DB is treated as read-only."""
        return self.app_env.strip().lower() in ("local", "dev", "development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
