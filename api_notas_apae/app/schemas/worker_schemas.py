from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums.execucao_status import ExecucaoStatus
from app.schemas.worker_output import (
    ObterProximaNotaOutput,
    WorkerExecucaoOutput,
)


class WorkerNotaClaimResponse(BaseModel):
    nota_id: UUID
    execucao_id: UUID
    chave: str
    tentativa: int

    @classmethod
    def from_output(cls, output: ObterProximaNotaOutput) -> "WorkerNotaClaimResponse":
        return cls(
            nota_id=output.nota_id,
            execucao_id=output.execucao_id,
            chave=output.chave,
            tentativa=output.tentativa,
        )


class WorkerResultadoRequest(BaseModel):
    status: ExecucaoStatus
    mensagem: str | None = None
    valor: Decimal | None = None
    data_emissao: date | None = None
    tempo_segundos: Decimal | None = None


class WorkerExecucaoResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    execucao_id: UUID
    nota_id: UUID
    tentativa: int
    status: ExecucaoStatus
    iniciado_em: datetime | None
    finalizado_em: datetime | None

    @classmethod
    def from_output(cls, output: WorkerExecucaoOutput) -> "WorkerExecucaoResponse":
        return cls(
            execucao_id=output.execucao_id,
            nota_id=output.nota_id,
            tentativa=output.tentativa,
            status=output.status,
            iniciado_em=output.iniciado_em,
            finalizado_em=output.finalizado_em,
        )
