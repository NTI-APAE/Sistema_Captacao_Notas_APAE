from pydantic import BaseModel, Field

from app.schemas.submissao_schemas import RegistrarSubmissaoResponse


class ProcessarImagemResponse(BaseModel):
    received: bool = True
    saved: bool
    replayed: bool = False
    qr_code_found: bool = False
    reason: str | None = None
    urls_consulta: list[str] = Field(default_factory=list)
    submissoes: list[RegistrarSubmissaoResponse] = Field(default_factory=list)
