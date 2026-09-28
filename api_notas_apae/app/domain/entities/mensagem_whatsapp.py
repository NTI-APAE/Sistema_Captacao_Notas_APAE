from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.domain.time import utc_now


class DirecaoMensagem(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class TipoMensagem(StrEnum):
    TEXTO = "TEXTO"
    IMAGEM = "IMAGEM"
    DOCUMENTO = "DOCUMENTO"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    STICKER = "STICKER"
    OUTRO = "OUTRO"


@dataclass(slots=True)
class MensagemWhatsApp:
    pessoa_id: UUID
    whatsapp_message_id: str
    instancia: str
    direcao: DirecaoMensagem
    tipo: TipoMensagem
    remote_jid: str
    raw_payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    texto: str | None = None
    mime_type: str | None = None
    media_path: str | None = None
    data_mensagem: datetime = field(default_factory=utc_now)
    criado_em: datetime = field(default_factory=utc_now)
