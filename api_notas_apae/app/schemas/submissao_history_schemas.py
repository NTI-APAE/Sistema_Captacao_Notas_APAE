from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums.origem_submissao import OrigemSubmissao
from app.domain.enums.submissao_status import SubmissaoStatus
from app.schemas.submissao_output import SubmissaoOutput


class SubmissaoNotaResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

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
    def from_output(cls, output: SubmissaoOutput) -> "SubmissaoNotaResponse":
        return cls(
            id=output.id,
            pessoa_id=output.pessoa_id,
            nota_fiscal_id=output.nota_fiscal_id,
            origem=output.origem,
            chave_extraida=output.chave_extraida,
            status=output.status,
            erro_codigo=output.erro_codigo,
            erro_mensagem=output.erro_mensagem,
            data_recebimento=output.data_recebimento,
            criado_em=output.criado_em,
        )
