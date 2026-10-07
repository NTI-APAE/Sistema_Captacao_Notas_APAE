"""Persiste os resumos de cada operacao do leitor de notas."""

import sqlalchemy as sa

from alembic import op

revision = "202610070001"
down_revision = "202609300001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resumos_operacao_leitor",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operacao_id", sa.Uuid(), nullable=False),
        sa.Column("total_notas", sa.Integer(), nullable=False),
        sa.Column("tentadas", sa.Integer(), nullable=False),
        sa.Column("cadastradas", sa.Integer(), nullable=False),
        sa.Column("duplicadas", sa.Integer(), nullable=False),
        sa.Column("ignoradas", sa.Integer(), nullable=False),
        sa.Column("erros", sa.Integer(), nullable=False),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_cadastradas", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_duplicadas", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_ignoradas", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_erros", sa.Numeric(14, 2), nullable=False),
        sa.Column("tempo_total_segundos", sa.Numeric(14, 3), nullable=False),
        sa.Column("tempo_notas_segundos", sa.Numeric(14, 3), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operacao_id", name="uq_resumos_operacao_leitor_operacao"),
    )
    op.create_index(
        "ix_resumos_operacao_leitor_operacao_id",
        "resumos_operacao_leitor",
        ["operacao_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resumos_operacao_leitor_operacao_id",
        table_name="resumos_operacao_leitor",
    )
    op.drop_table("resumos_operacao_leitor")
