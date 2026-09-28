from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExecucaoCadastroModel(Base):
    __tablename__ = "execucoes_cadastro"
    __table_args__ = (
        UniqueConstraint(
            "nota_fiscal_id",
            "tentativa",
            name="uq_execucoes_cadastro_nota_tentativa",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nota_fiscal_id: Mapped[UUID] = mapped_column(
        ForeignKey("notas_fiscais.id"),
        index=True,
    )
    tentativa: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(40))
    mensagem: Mapped[str | None] = mapped_column(String(500), nullable=True)
    workflow_execution_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    valor_obtido: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    data_emissao_obtida: Mapped[date | None] = mapped_column(Date, nullable=True)
    tempo_segundos: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3),
        nullable=True,
    )
    iniciado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finalizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
