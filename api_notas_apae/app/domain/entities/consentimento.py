from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums.consentimento_tipo import ConsentimentoTipo
from app.domain.time import utc_now


@dataclass(slots=True)
class Consentimento:
    pessoa_id: UUID
    tipo: ConsentimentoTipo
    aceito: bool
    origem: str
    id: UUID = field(default_factory=uuid4)
    data_resposta: datetime = field(default_factory=utc_now)
