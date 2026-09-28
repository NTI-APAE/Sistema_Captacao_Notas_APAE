"""Mapeamento da tabela já criada pela migration inicial; somente consulta no painel."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConsentimentoModel(Base):
    __tablename__ = "consentimentos"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    pessoa_id: Mapped[UUID] = mapped_column(ForeignKey("pessoas.id"))
    tipo: Mapped[str] = mapped_column(String(60))
    aceito: Mapped[bool] = mapped_column()
    origem: Mapped[str] = mapped_column(String(100))
    data_resposta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
