from dataclasses import dataclass
from uuid import UUID

from app.domain.enums.submissao_status import SubmissaoStatus


@dataclass(frozen=True, slots=True)
class RegistrarSubmissaoOutput:
    status: SubmissaoStatus
    duplicada: bool
    nota_id: UUID
    submissao_id: UUID
