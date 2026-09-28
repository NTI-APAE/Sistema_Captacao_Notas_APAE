from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums.origem_submissao import OrigemSubmissao
from app.domain.enums.submissao_status import SubmissaoStatus
from app.domain.time import utc_now


@dataclass(slots=True)
class SubmissaoNota:
    pessoa_id: UUID | None
    origem: OrigemSubmissao
    status: SubmissaoStatus
    id: UUID = field(default_factory=uuid4)
    mensagem_whatsapp_id: UUID | None = None
    arquivo_importado_id: UUID | None = None
    nota_fiscal_id: UUID | None = None
    imagem_path: str | None = None
    chave_extraida: str | None = None
    erro_codigo: str | None = None
    erro_mensagem: str | None = None
    data_recebimento: datetime = field(default_factory=utc_now)
    criado_em: datetime = field(default_factory=utc_now)
