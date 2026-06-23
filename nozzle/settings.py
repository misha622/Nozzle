from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOZZLE_",
        extra="ignore",
        case_sensitive=False,
    )

    # Environment
    env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"

    # Database
    database_url: str = "sqlite+aiosqlite:///nozzle.db"
    database_url_sync: str = "sqlite:///nozzle.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Auth
    api_key: str = ""

    # Alert limits per tier
    free_alert_limit_daily: int = 1000
    pro_alert_limit_daily: int = 50000

    # ML
    ml_model_dir: str = "models"
    ml_retrain_interval_hours: int = 24
    ml_min_samples_for_training: int = 100

    # Clustering
    clustering_window_minutes: int = 5
    clustering_min_alerts: int = 3


settings = Settings()