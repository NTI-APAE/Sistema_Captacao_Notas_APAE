from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResumoOperacaoLeitorModel(Base):
    __tablename__ = "resumos_operacao_leitor"
    __table_args__ = (
        UniqueConstraint("operacao_id", name="uq_resumos_operacao_leitor_operacao"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    operacao_id: Mapped[UUID] = mapped_column(index=True)
    total_notas: Mapped[int] = mapped_column(Integer)
    tentadas: Mapped[int] = mapped_column(Integer)
    cadastradas: Mapped[int] = mapped_column(Integer)
    duplicadas: Mapped[int] = mapped_column(Integer)
    ignoradas: Mapped[int] = mapped_column(Integer)
    erros: Mapped[int] = mapped_column(Integer)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    valor_cadastradas: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    valor_duplicadas: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    valor_ignoradas: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    valor_erros: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tempo_total_segundos: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    tempo_notas_segundos: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
