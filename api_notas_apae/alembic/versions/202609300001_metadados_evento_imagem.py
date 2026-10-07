"""Persist message metadata and link WhatsApp image events to submissions."""

import sqlalchemy as sa

from alembic import op

revision = "202609300001"
down_revision = "202609280001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for _name, column in (
        ("remote_jid", sa.Column("remote_jid", sa.String(255), nullable=True)),
        ("remote_jid_alt", sa.Column("remote_jid_alt", sa.String(255), nullable=True)),
        ("from_me", sa.Column("from_me", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("message_type", sa.Column("message_type", sa.String(100), nullable=True)),
        ("data_mensagem", sa.Column("data_mensagem", sa.DateTime(timezone=True), nullable=True)),
        ("push_name", sa.Column("push_name", sa.String(255), nullable=True)),
        ("mimetype", sa.Column("mimetype", sa.String(100), nullable=True)),
        ("caption", sa.Column("caption", sa.Text(), nullable=True)),
        ("reenvios", sa.Column("reenvios", sa.Integer(), nullable=False, server_default="0")),
        ("ultimo_reenvio_em", sa.Column("ultimo_reenvio_em", sa.DateTime(timezone=True), nullable=True)),
    ):
        op.add_column("eventos_imagem", column)
    op.add_column(
        "submissoes_nota",
        sa.Column("evento_instancia", sa.String(100), nullable=True),
    )
    op.add_column(
        "submissoes_nota",
        sa.Column("evento_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_submissoes_nota_evento",
        "submissoes_nota",
        ["origem", "evento_instancia", "evento_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_submissoes_nota_evento", table_name="submissoes_nota")
    op.drop_column("submissoes_nota", "evento_id")
    op.drop_column("submissoes_nota", "evento_instancia")
    for name in (
        "ultimo_reenvio_em",
        "reenvios",
        "caption",
        "mimetype",
        "push_name",
        "data_mensagem",
        "message_type",
        "from_me",
        "remote_jid_alt",
        "remote_jid",
    ):
        op.drop_column("eventos_imagem", name)
