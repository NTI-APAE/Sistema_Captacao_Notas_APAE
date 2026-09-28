"""Recibos de imagem para idempotência; preserva todas as tabelas existentes."""

import sqlalchemy as sa

from alembic import op

revision = "202609210001"
down_revision = "202609020003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eventos_imagem",
        sa.Column("origem", sa.String(40), nullable=False),
        sa.Column("instancia", sa.String(100), nullable=False),
        sa.Column("evento_id", sa.String(255), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("resultado", sa.JSON(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("origem", "instancia", "evento_id"),
    )


def downgrade() -> None:
    # Operação explícita de rollback da migration, nunca executada no startup.
    op.drop_table("eventos_imagem")
