from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums.execucao_status import ExecucaoStatus


@dataclass(frozen=True, slots=True)
class ObterProximaNotaOutput:
    nota_id: UUID
    execucao_id: UUID
    chave: str
    tentativa: int


@dataclass(frozen=True, slots=True)
class WorkerExecucaoOutput:
    execucao_id: UUID
    nota_id: UUID
    tentativa: int
    status: ExecucaoStatus
    iniciado_em: datetime | None
    finalizado_em: datetime | None
