"""add phase 2 indexes

Revision ID: 202609020002
Revises: 202609020001
Create Date: 2026-09-02 16:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202609020002"
down_revision: str | None = "202609020001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_submissoes_nota_pessoa_id",
        "submissoes_nota",
        ["pessoa_id"],
    )
    op.create_index(
        "ix_submissoes_nota_nota_fiscal_id",
        "submissoes_nota",
        ["nota_fiscal_id"],
    )
    op.create_index(
        "ix_execucoes_cadastro_nota_fiscal_id",
        "execucoes_cadastro",
        ["nota_fiscal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_execucoes_cadastro_nota_fiscal_id",
        table_name="execucoes_cadastro",
    )
    op.drop_index(
        "ix_submissoes_nota_nota_fiscal_id",
        table_name="submissoes_nota",
    )
    op.drop_index(
        "ix_submissoes_nota_pessoa_id",
        table_name="submissoes_nota",
    )
