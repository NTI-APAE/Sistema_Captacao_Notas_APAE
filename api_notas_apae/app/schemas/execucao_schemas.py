from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums.execucao_status import ExecucaoStatus
from app.schemas.execucao_cadastro_output import ExecucaoCadastroOutput


class RegistrarResultadoCadastroRequest(BaseModel):
    status: ExecucaoStatus
    execucao_id: UUID
    mensagem: str | None = None
    valor: Decimal | None = None
    data_emissao: date | None = None
    tempo_segundos: Decimal | None = None


class ExecucaoCadastroResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID
    nota_fiscal_id: UUID
    tentativa: int
    status: ExecucaoStatus
    mensagem: str | None
    valor_obtido: Decimal | None
    data_emissao_obtida: date | None
    tempo_segundos: Decimal | None
    iniciado_em: datetime | None
    finalizado_em: datetime | None
    criado_em: datetime

    @classmethod
    def from_output(cls, output: ExecucaoCadastroOutput) -> "ExecucaoCadastroResponse":
        return cls(
            id=output.id,
            nota_fiscal_id=output.nota_fiscal_id,
            tentativa=output.tentativa,
            status=output.status,
            mensagem=output.mensagem,
            valor_obtido=output.valor_obtido,
            data_emissao_obtida=output.data_emissao_obtida,
            tempo_segundos=output.tempo_segundos,
            iniciado_em=output.iniciado_em,
            finalizado_em=output.finalizado_em,
            criado_em=output.criado_em,
        )
