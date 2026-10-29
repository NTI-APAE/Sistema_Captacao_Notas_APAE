from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_DATABASE_URL = (
    "postgresql+psycopg://notas_apae:notas_apae@localhost:5433/notas_apae"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: Literal["development", "test", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    database_url: str = Field(
        default=DEVELOPMENT_DATABASE_URL,
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
    worker_max_attempts: int = Field(default=3, ge=1, alias="WORKER_MAX_ATTEMPTS")
    notas_api_internal_key: str = Field(default="", alias="NOTAS_API_INTERNAL_KEY")
    worker_execution_timeout_minutes: int = Field(
        default=30,
        alias="WORKER_EXECUTION_TIMEOUT_MINUTES",
    )
    worker_heartbeat_interval_seconds: int = Field(
        default=30, ge=5, alias="WORKER_HEARTBEAT_INTERVAL_SECONDS"
    )
    worker_lease_timeout_seconds: int = Field(
        default=120, ge=15, alias="WORKER_LEASE_TIMEOUT_SECONDS"
    )
    admin_session_cookie: str = Field(
        default="apae_session", alias="ADMIN_SESSION_COOKIE"
    )
    admin_session_minutes: int = Field(
        default=480, ge=15, le=10080, alias="ADMIN_SESSION_MINUTES"
    )
    admin_cookie_secure: bool = Field(default=False, alias="ADMIN_COOKIE_SECURE")

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.environment != "production":
            return self

        missing = []
        if not self.database_url or self.database_url == DEVELOPMENT_DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.worker_api_key:
            missing.append("WORKER_API_KEY")
        if not self.notas_api_internal_key:
            missing.append("NOTAS_API_INTERNAL_KEY")
        if not self.admin_cookie_secure:
            raise ValueError("ADMIN_COOKIE_SECURE deve ser true em produção")
        if missing:
            raise ValueError(
                "Variáveis obrigatórias ausentes em produção: "
                + ", ".join(missing)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
