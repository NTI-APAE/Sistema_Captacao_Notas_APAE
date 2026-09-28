from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums.nota_status import NotaStatus
from app.domain.enums.submissao_status import SubmissaoStatus

TIMEZONE = ZoneInfo("America/Sao_Paulo")


def inicio_dia(value: date) -> datetime:
    return datetime.combine(value, time.min, TIMEZONE).astimezone(UTC)


class AdminReportingFilter(BaseModel):
    page: int = Field(default=1, ge=1)
    consent_page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    data_inicial: date | None = None
    data_final: date | None = None
    status: SubmissaoStatus | None = None
    cadastro: NotaStatus | None = None
    telefone: str = Field(default="", max_length=30)
    chave: str = Field(default="", max_length=44)
    q: str = Field(default="", max_length=100)
    duplicada: bool | None = None
    ativo: bool | None = None
    comunicacao: bool | None = None
    ligacao: bool | None = None

    @field_validator("*", mode="before")
    @classmethod
    def vazio(cls, value, info):
        if value == "" and info.field_name not in {"q", "telefone", "chave"}:
            return None
        return value

    @model_validator(mode="after")
    def periodo(self):
        if self.data_inicial and self.data_final:
            if self.data_final < self.data_inicial:
                raise ValueError("A data final deve ser igual ou posterior à inicial")
        if self.data_final == date.max:
            raise ValueError("Data final fora do intervalo suportado")
        return self

    @property
    def inicio(self):
        return inicio_dia(self.data_inicial) if self.data_inicial else None

    @property
    def fim(self):
        return (
            inicio_dia(self.data_final + timedelta(days=1)) if self.data_final else None
        )
