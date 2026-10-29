from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums.execucao_fase import ExecucaoFase
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
    worker_id: str
    lease_expira_em: datetime

    @classmethod
    def from_output(cls, output: ObterProximaNotaOutput) -> "WorkerNotaClaimResponse":
        return cls(
            nota_id=output.nota_id,
            execucao_id=output.execucao_id,
            chave=output.chave,
            tentativa=output.tentativa,
            worker_id=output.worker_id,
            lease_expira_em=output.lease_expira_em,
        )


class WorkerResultadoRequest(BaseModel):
    status: ExecucaoStatus
    mensagem: str | None = None
    valor: Decimal | None = None
    data_emissao: date | None = None
    tempo_segundos: Decimal | None = None


class WorkerHeartbeatRequest(BaseModel):
    fase: ExecucaoFase | None = None
    mensagem: str | None = None


class WorkerExecucaoResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    execucao_id: UUID
    nota_id: UUID
    tentativa: int
    status: ExecucaoStatus
    iniciado_em: datetime | None
    finalizado_em: datetime | None
    ultimo_heartbeat_em: datetime | None = None
    lease_expira_em: datetime | None = None
    fase_portal: str = "RESERVADA"

    @classmethod
    def from_output(cls, output: WorkerExecucaoOutput) -> "WorkerExecucaoResponse":
        return cls(
            execucao_id=output.execucao_id,
            nota_id=output.nota_id,
            tentativa=output.tentativa,
            status=output.status,
            iniciado_em=output.iniciado_em,
            finalizado_em=output.finalizado_em,
            ultimo_heartbeat_em=output.ultimo_heartbeat_em,
            lease_expira_em=output.lease_expira_em,
            fase_portal=output.fase_portal,
        )
