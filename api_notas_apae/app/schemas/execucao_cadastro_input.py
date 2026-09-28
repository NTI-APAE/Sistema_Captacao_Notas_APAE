from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.enums.execucao_status import ExecucaoStatus


@dataclass(frozen=True, slots=True)
class RegistrarResultadoCadastroInput:
    execucao_id: UUID
    status: ExecucaoStatus
    nota_id: UUID | None = None
    mensagem: str | None = None
    valor: Decimal | None = None
    data_emissao: date | None = None
    tempo_segundos: Decimal | None = None
