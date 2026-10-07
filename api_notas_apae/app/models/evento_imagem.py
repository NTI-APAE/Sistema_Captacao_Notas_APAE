from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
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
    remote_jid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_jid_alt: Mapped[str | None] = mapped_column(String(255), nullable=True)
    from_me: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_mensagem: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    push_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mimetype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    reenvios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ultimo_reenvio_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
