from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .submissao_nota_model import SubmissaoNotaModel


class NotaFiscalModel(Base):
    __tablename__ = "notas_fiscais"
    __table_args__ = (
        CheckConstraint("length(chave) = 44", name="ck_notas_fiscais_chave_44"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(44), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    mensagem_status: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    data_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_cadastro: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    submissoes: Mapped[list[SubmissaoNotaModel]] = relationship(
        back_populates="nota_fiscal",
    )
