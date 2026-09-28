"""Sessões administrativas opacas com revogação e expiração."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202609280001"
down_revision: str | None = "202609210001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios_admin",
        sa.Column("falhas_login", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "usuarios_admin",
        sa.Column("bloqueado_ate", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "sessoes_admin",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios_admin.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "ultimo_uso_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("token_hash", name="uq_sessoes_admin_token_hash"),
    )
    op.create_index("ix_sessoes_admin_token_hash", "sessoes_admin", ["token_hash"])
    op.create_index("ix_sessoes_admin_usuario_id", "sessoes_admin", ["usuario_id"])
    op.create_index("ix_sessoes_admin_expira_em", "sessoes_admin", ["expira_em"])


def downgrade() -> None:
    op.drop_index("ix_sessoes_admin_expira_em", table_name="sessoes_admin")
    op.drop_index("ix_sessoes_admin_usuario_id", table_name="sessoes_admin")
    op.drop_index("ix_sessoes_admin_token_hash", table_name="sessoes_admin")
    op.drop_table("sessoes_admin")
    op.drop_column("usuarios_admin", "bloqueado_ate")
    op.drop_column("usuarios_admin", "falhas_login")
