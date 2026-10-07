from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities.resumo_operacao_leitor import ResumoOperacaoLeitor


class RegistrarResumoOperacaoLeitorRequest(BaseModel):
    operacao_id: UUID
    total_notas: int = Field(ge=0)
    tentadas: int = Field(ge=0)
    cadastradas: int = Field(ge=0)
    duplicadas: int = Field(ge=0)
    ignoradas: int = Field(ge=0)
    erros: int = Field(ge=0)
    valor_total: Decimal = Field(ge=0)
    valor_cadastradas: Decimal = Field(ge=0)
    valor_duplicadas: Decimal = Field(ge=0)
    valor_ignoradas: Decimal = Field(ge=0)
    valor_erros: Decimal = Field(ge=0)
    tempo_total_segundos: Decimal = Field(ge=0)
    tempo_notas_segundos: Decimal = Field(ge=0)


class ResumoOperacaoLeitorResponse(BaseModel):
    id: UUID
    operacao_id: UUID
    total_notas: int
    tentadas: int
    cadastradas: int
    duplicadas: int
    ignoradas: int
    erros: int
    valor_total: Decimal
    valor_cadastradas: Decimal
    valor_duplicadas: Decimal
    valor_ignoradas: Decimal
    valor_erros: Decimal
    tempo_total_segundos: Decimal
    tempo_notas_segundos: Decimal

    @classmethod
    def from_domain(
        cls,
        resumo: ResumoOperacaoLeitor,
    ) -> "ResumoOperacaoLeitorResponse":
        return cls(
            id=resumo.id,
            operacao_id=resumo.operacao_id,
            total_notas=resumo.total_notas,
            tentadas=resumo.tentadas,
            cadastradas=resumo.cadastradas,
            duplicadas=resumo.duplicadas,
            ignoradas=resumo.ignoradas,
            erros=resumo.erros,
            valor_total=resumo.valor_total,
            valor_cadastradas=resumo.valor_cadastradas,
            valor_duplicadas=resumo.valor_duplicadas,
            valor_ignoradas=resumo.valor_ignoradas,
            valor_erros=resumo.valor_erros,
            tempo_total_segundos=resumo.tempo_total_segundos,
            tempo_notas_segundos=resumo.tempo_notas_segundos,
        )
