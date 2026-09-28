"""Contrato público do frontend; listas nunca transportam chave/telefone completos."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


class AdminReportingDTO(BaseModel):
    @field_validator("*", mode="after")
    @classmethod
    def timestamp_utc(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Pagina[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class NotaDetalhe(AdminReportingDTO):
    id: UUID
    data_recebimento: datetime
    status: str
    origem: str
    pessoa_id: UUID | None
    nota_fiscal_id: UUID | None
    mensagem_whatsapp_id: UUID | None
    erro_codigo: str | None
    chave: str | None
    nome: str | None
    telefone: str | None
    cadastro: str | None
    data_cadastro: datetime | None
    valor: Decimal | None
    data_emissao: date | None


class NotaLista(AdminReportingDTO):
    id: UUID
    data_recebimento: datetime
    status: str
    origem: str
    pessoa_id: UUID | None
    nome: str | None
    telefone: str | None
    chave: str | None
    cadastro: str | None

    @field_validator("telefone")
    @classmethod
    def telefone_mascarado(cls, value):
        return "•••• " + value[-4:] if value else None

    @field_validator("chave")
    @classmethod
    def chave_mascarada(cls, value):
        return value[:4] + "…" + value[-5:] if value else None


class ContatoDetalhe(AdminReportingDTO):
    id: UUID
    nome: str | None
    telefone: str
    ativo: bool
    criado_em: datetime
    primeiro_envio: datetime | None
    ultimo_envio: datetime | None
    envios: int
    notas: int
    comunicacao: bool | None
    ligacao: bool | None


class ContatoLista(ContatoDetalhe):
    @field_validator("telefone")
    @classmethod
    def telefone_mascarado(cls, value):
        return "•••• " + value[-4:]


class ConsentimentoDTO(AdminReportingDTO):
    tipo: str
    aceito: bool
    origem: str
    data_resposta: datetime


class HistoricoContato(BaseModel):
    contato: ContatoDetalhe
    result: Pagina[NotaLista]
    consentimentos: Pagina[ConsentimentoDTO]


class Indicadores(BaseModel):
    total: int
    hoje: int
    mes: int
    duplicadas: int
    falhas: int
    notas: int
    cadastradas: int
    contatos: int
    novos_contatos: int
    imagens_sem_chave: int


class DiaRecebimento(BaseModel):
    dia: date
    total: int


class ResumoAdmin(BaseModel):
    indicadores: Indicadores
    series: list[DiaRecebimento]
    maximo: int
    status_submissoes: list[tuple[str, int]]
    status_notas: list[tuple[str, int]]
    result: Pagina[NotaLista]
