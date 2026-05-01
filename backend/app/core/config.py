from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = "change-me"
    app_allowed_hosts: list[str] = ["localhost", "127.0.0.1"]

    # Database
    database_url: str = "postgresql+asyncpg://rezeb:rezeb_dev_password@postgres:5432/rezeb"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_queue_url: str = "redis://redis:6379/1"

    # S3
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_photos: str = "rezeb-photos"
    s3_bucket_docs: str = "rezeb-docs"
    s3_region: str = "ru-central1"

    # AITUNNEL / LLM
    aitunnel_base_url: str = "https://api.aitunnel.ru/v1"
    aitunnel_api_key: str = ""
    model_vision: str = "claude-sonnet-4-6"
    model_complex: str = "claude-opus-4-7"
    model_fast: str = "claude-haiku-4-5-20251001"
    model_embeddings: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072

    # ML Service
    ml_service_url: str = "http://ml-service:8001"
    yolo_confidence_threshold: float = 0.45
    escalation_confidence_threshold: float = 0.70

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # Rate limits
    rate_limit_per_user: int = 60
    rate_limit_window_seconds: int = 60

    # Usage limits
    daily_control_limit_per_user: int = 50
    daily_pto_limit_per_user: int = 200
    monthly_llm_budget_rub: float = 30000.0
    budget_alert_threshold: float = 0.80

    # Email (SMTP)
    smtp_host: str = "smtp.yandex.ru"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@rezeb.ru"
    smtp_use_tls: bool = True

    # External monitoring
    sentry_dsn: str = ""
    telegram_bot_token: str = ""
    telegram_alert_chat_id: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("app_allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def split_comma(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [h.strip() for h in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
