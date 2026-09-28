from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.time import utc_now


def normalizar_telefone(telefone: str) -> str:
    return "".join(caractere for caractere in telefone if caractere.isdigit())


@dataclass(slots=True)
class Pessoa:
    telefone: str
    id: UUID = field(default_factory=uuid4)
    nome: str | None = None
    ativo: bool = True
    criado_em: datetime = field(default_factory=utc_now)
    atualizado_em: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.telefone = normalizar_telefone(self.telefone)
        if not self.telefone:
            raise ValueError("telefone e obrigatorio")
