"""Application settings via pydantic-settings, loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """OneAI-Cortex configuration. All values loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === App ===
    app_name: str = "OneAI-Cortex"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # === Auth (shared with OneAI-Auth) ===
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    # === Encryption ===
    encryption_key: str

    # === Database ===
    database_url: str = "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_echo: bool = False

    # === Redis ===
    redis_url: str = "redis://localhost:6379/0"

    # === OneAI-Auth (HARD DEPENDENCY) ===
    auth_service_url: str = "http://localhost:8001"

    # === Google OAuth (optional — feature disabled if empty) ===
    google_client_id: str = ""
    google_client_secret: str = ""

    # === Agent Execution ===
    agent_execution_timeout_seconds: int = 120

    # === Checkpointing ===
    checkpoint_dir: str = "data/checkpoints"
    checkpoint_retention_days: int = 7

    # === Telemetry ===
    otlp_endpoint: str = "http://localhost:4317"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance. Creates on first call."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
