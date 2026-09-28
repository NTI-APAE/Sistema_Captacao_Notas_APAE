from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.domain.enums.processamento_status import ProcessamentoStatus
from app.domain.time import utc_now


class ProcessamentoEtapa(StrEnum):
    RECEBIMENTO = "RECEBIMENTO"
    QR_CODE = "QR_CODE"
    OCR = "OCR"
    VALIDACAO_CHAVE = "VALIDACAO_CHAVE"
    DUPLICIDADE = "DUPLICIDADE"


@dataclass(slots=True)
class ProcessamentoNota:
    submissao_id: UUID
    etapa: ProcessamentoEtapa
    status: ProcessamentoStatus
    tentativa: int
    id: UUID = field(default_factory=uuid4)
    mensagem: str | None = None
    detalhes: dict[str, Any] | None = None
    iniciado_em: datetime = field(default_factory=utc_now)
    finalizado_em: datetime | None = None
