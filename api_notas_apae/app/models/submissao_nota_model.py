from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .nota_fiscal_model import NotaFiscalModel
    from .pessoa_model import PessoaModel


class SubmissaoNotaModel(Base):
    __tablename__ = "submissoes_nota"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    pessoa_id: Mapped[UUID | None] = mapped_column(ForeignKey("pessoas.id"))
    mensagem_whatsapp_id: Mapped[UUID | None] = mapped_column(nullable=True)
    arquivo_importado_id: Mapped[UUID | None] = mapped_column(nullable=True)
    nota_fiscal_id: Mapped[UUID | None] = mapped_column(ForeignKey("notas_fiscais.id"))
    origem: Mapped[str] = mapped_column(String(40), index=True)
    imagem_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    chave_extraida: Mapped[str | None] = mapped_column(String(44), nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    erro_codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    erro_mensagem: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_recebimento: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    pessoa: Mapped[PessoaModel | None] = relationship(back_populates="submissoes")
    nota_fiscal: Mapped[NotaFiscalModel | None] = relationship(
        back_populates="submissoes",
    )
