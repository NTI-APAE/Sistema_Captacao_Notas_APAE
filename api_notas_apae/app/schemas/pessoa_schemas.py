from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.pessoa_output import PessoaOutput


class PessoaResponse(BaseModel):
    id: UUID
    telefone: str
    nome: str | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def from_output(cls, output: PessoaOutput) -> "PessoaResponse":
        return cls(
            id=output.id,
            telefone=output.telefone,
            nome=output.nome,
            ativo=output.ativo,
            criado_em=output.criado_em,
            atualizado_em=output.atualizado_em,
        )
