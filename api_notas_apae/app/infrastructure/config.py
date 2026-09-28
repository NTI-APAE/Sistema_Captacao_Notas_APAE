from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default="postgresql+psycopg://notas_apae:notas_apae@localhost:5433/notas_apae",
        alias="DATABASE_URL",
    )
    evolution_base_url: str = Field(default="", alias="EVOLUTION_BASE_URL")
    evolution_api_key: str = Field(default="", alias="EVOLUTION_API_KEY")
    evolution_instance: str = Field(default="default", alias="EVOLUTION_INSTANCE")
    n8n_webhook_url: str = Field(default="", alias="N8N_WEBHOOK_URL")
    prazo_maximo_emissao_meses: int = Field(
        default=3,
        alias="PRAZO_MAXIMO_EMISSAO_MESES",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    worker_api_key: str = Field(default="", alias="WORKER_API_KEY")
    notas_internal_api_key: str = Field(default="", alias="NOTAS_INTERNAL_API_KEY")
    webhook_token: str = Field(default="", alias="WEBHOOK_TOKEN")
    worker_execution_timeout_minutes: int = Field(
        default=30,
        alias="WORKER_EXECUTION_TIMEOUT_MINUTES",
    )
    admin_session_cookie: str = Field(
        default="apae_session", alias="ADMIN_SESSION_COOKIE"
    )
    admin_session_minutes: int = Field(
        default=480, ge=15, le=10080, alias="ADMIN_SESSION_MINUTES"
    )
    admin_cookie_secure: bool = Field(default=False, alias="ADMIN_COOKIE_SECURE")


@lru_cache
def get_settings() -> Settings:
    return Settings()
