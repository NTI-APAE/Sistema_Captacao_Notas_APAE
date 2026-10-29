"""Adiciona lease e estado de reconciliação ao worker."""

import sqlalchemy as sa

from alembic import op

revision = "202610210001"
down_revision = "202610070001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "execucoes_cadastro", sa.Column("worker_id", sa.String(100), nullable=True)
    )
    op.add_column(
        "execucoes_cadastro",
        sa.Column("ultimo_heartbeat_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "execucoes_cadastro",
        sa.Column("lease_expira_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "execucoes_cadastro",
        sa.Column(
            "fase_portal",
            sa.String(40),
            nullable=False,
            server_default="LEGACY_DESCONHECIDA",
        ),
    )
    op.add_column(
        "execucoes_cadastro",
        sa.Column(
            "efeito_externo_iniciado_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "execucoes_cadastro",
        sa.Column("motivo_recuperacao", sa.String(500), nullable=True),
    )
    op.create_index(
        "ix_execucoes_cadastro_status_lease",
        "execucoes_cadastro",
        ["status", "lease_expira_em"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_execucoes_cadastro_status_lease", table_name="execucoes_cadastro"
    )
    op.drop_column("execucoes_cadastro", "motivo_recuperacao")
    op.drop_column("execucoes_cadastro", "efeito_externo_iniciado_em")
    op.drop_column("execucoes_cadastro", "fase_portal")
    op.drop_column("execucoes_cadastro", "lease_expira_em")
    op.drop_column("execucoes_cadastro", "ultimo_heartbeat_em")
    op.drop_column("execucoes_cadastro", "worker_id")
