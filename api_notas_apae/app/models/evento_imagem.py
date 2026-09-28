from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventoImagem(Base):
    """Recibo atômico. Não armazena a imagem nem o payload do WhatsApp."""

    __tablename__ = "eventos_imagem"

    origem: Mapped[str] = mapped_column(String(40), primary_key=True)
    instancia: Mapped[str] = mapped_column(String(100), primary_key=True)
    evento_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    resultado: Mapped[dict] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
