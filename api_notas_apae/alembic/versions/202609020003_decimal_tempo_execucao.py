"""use decimal execution time

Revision ID: 202609020003
Revises: 202609020002
Create Date: 2026-09-02 16:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202609020003"
down_revision: str | None = "202609020002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "execucoes_cadastro",
        "tempo_segundos",
        existing_type=sa.Integer(),
        type_=sa.Numeric(12, 3),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "execucoes_cadastro",
        "tempo_segundos",
        existing_type=sa.Numeric(12, 3),
        type_=sa.Integer(),
        existing_nullable=True,
    )
