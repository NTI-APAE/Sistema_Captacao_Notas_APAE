from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.enums.nota_status import NotaStatus


@dataclass(frozen=True, slots=True)
class NotaOutput:
    id: UUID
    chave: str
    status: NotaStatus
    mensagem_status: str | None
    valor: Decimal | None
    data_emissao: date | None
    data_cadastro: datetime | None
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def from_domain(cls, nota: NotaFiscal) -> "NotaOutput":
        return cls(
            id=nota.id,
            chave=nota.chave,
            status=nota.status,
            mensagem_status=nota.mensagem_status,
            valor=nota.valor,
            data_emissao=nota.data_emissao,
            data_cadastro=nota.data_cadastro,
            criado_em=nota.criado_em,
            atualizado_em=nota.atualizado_em,
        )
