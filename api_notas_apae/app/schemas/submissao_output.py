from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.submissao_nota import SubmissaoNota
from app.domain.enums.origem_submissao import OrigemSubmissao
from app.domain.enums.submissao_status import SubmissaoStatus


@dataclass(frozen=True, slots=True)
class SubmissaoOutput:
    id: UUID
    pessoa_id: UUID | None
    nota_fiscal_id: UUID | None
    origem: OrigemSubmissao
    chave_extraida: str | None
    status: SubmissaoStatus
    erro_codigo: str | None
    erro_mensagem: str | None
    data_recebimento: datetime
    criado_em: datetime

    @classmethod
    def from_domain(cls, submissao: SubmissaoNota) -> "SubmissaoOutput":
        return cls(
            id=submissao.id,
            pessoa_id=submissao.pessoa_id,
            nota_fiscal_id=submissao.nota_fiscal_id,
            origem=submissao.origem,
            chave_extraida=submissao.chave_extraida,
            status=submissao.status,
            erro_codigo=submissao.erro_codigo,
            erro_mensagem=submissao.erro_mensagem,
            data_recebimento=submissao.data_recebimento,
            criado_em=submissao.criado_em,
        )
