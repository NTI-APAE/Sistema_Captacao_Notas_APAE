from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.pessoa import Pessoa


@dataclass(frozen=True, slots=True)
class PessoaOutput:
    id: UUID
    telefone: str
    nome: str | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def from_domain(cls, pessoa: Pessoa) -> "PessoaOutput":
        return cls(
            id=pessoa.id,
            telefone=pessoa.telefone,
            nome=pessoa.nome,
            ativo=pessoa.ativo,
            criado_em=pessoa.criado_em,
            atualizado_em=pessoa.atualizado_em,
        )
