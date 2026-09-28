from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums.origem_submissao import OrigemSubmissao
from app.domain.enums.submissao_status import SubmissaoStatus


class RegistrarSubmissaoRequest(BaseModel):
    telefone: str
    origem: OrigemSubmissao
    chave: str


class RegistrarSubmissaoResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: SubmissaoStatus
    duplicada: bool
    nota_id: UUID
    submissao_id: UUID
