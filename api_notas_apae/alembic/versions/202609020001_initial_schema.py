"""initial schema

Revision ID: 202609020001
Revises:
Create Date: 2026-09-02 15:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202609020001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pessoas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telefone", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("telefone", name="uq_pessoas_telefone"),
    )
    op.create_index("ix_pessoas_telefone", "pessoas", ["telefone"])

    op.create_table(
        "notas_fiscais",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chave", sa.String(length=44), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("mensagem_status", sa.String(length=500), nullable=True),
        sa.Column("valor", sa.Numeric(12, 2), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=True),
        sa.Column("data_cadastro", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("chave ~ '^[0-9]{44}$'", name="ck_notas_fiscais_chave_44"),
        sa.UniqueConstraint("chave", name="uq_notas_fiscais_chave"),
    )
    op.create_index("ix_notas_fiscais_chave", "notas_fiscais", ["chave"])
    op.create_index("ix_notas_fiscais_status", "notas_fiscais", ["status"])

    op.create_table(
        "mensagens_whatsapp",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pessoa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pessoas.id")),
        sa.Column("whatsapp_message_id", sa.String(length=255), nullable=False),
        sa.Column("instancia", sa.String(length=255), nullable=False),
        sa.Column("direcao", sa.String(length=20), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("remote_jid", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("media_path", sa.String(length=1000), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("data_mensagem", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("whatsapp_message_id", name="uq_mensagens_whatsapp_message_id"),
    )

    op.create_table(
        "arquivos_importados",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome_arquivo", sa.String(length=255), nullable=False),
        sa.Column("caminho_arquivo", sa.String(length=1000), nullable=False),
        sa.Column("total_linhas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_validas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_invalidas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duplicadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_importacao", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "submissoes_nota",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pessoa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pessoas.id"), nullable=True),
        sa.Column("mensagem_whatsapp_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mensagens_whatsapp.id"), nullable=True),
        sa.Column("arquivo_importado_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("arquivos_importados.id"), nullable=True),
        sa.Column("nota_fiscal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notas_fiscais.id"), nullable=True),
        sa.Column("origem", sa.String(length=40), nullable=False),
        sa.Column("imagem_path", sa.String(length=1000), nullable=True),
        sa.Column("chave_extraida", sa.String(length=44), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("erro_codigo", sa.String(length=100), nullable=True),
        sa.Column("erro_mensagem", sa.String(length=500), nullable=True),
        sa.Column("data_recebimento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_submissoes_nota_status", "submissoes_nota", ["status"])

    op.create_table(
        "consentimentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pessoa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pessoas.id"), nullable=False),
        sa.Column("tipo", sa.String(length=60), nullable=False),
        sa.Column("aceito", sa.Boolean(), nullable=False),
        sa.Column("origem", sa.String(length=100), nullable=False),
        sa.Column("data_resposta", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "processamentos_nota",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("submissao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissoes_nota.id"), nullable=False),
        sa.Column("etapa", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("tentativa", sa.Integer(), nullable=False),
        sa.Column("mensagem", sa.String(length=500), nullable=True),
        sa.Column("detalhes", postgresql.JSONB(), nullable=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "execucoes_cadastro",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nota_fiscal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notas_fiscais.id"), nullable=False),
        sa.Column("tentativa", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("mensagem", sa.String(length=500), nullable=True),
        sa.Column("workflow_execution_id", sa.String(length=255), nullable=True),
        sa.Column("valor_obtido", sa.Numeric(12, 2), nullable=True),
        sa.Column("data_emissao_obtida", sa.Date(), nullable=True),
        sa.Column("tempo_segundos", sa.Integer(), nullable=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("nota_fiscal_id", "tentativa", name="uq_execucoes_cadastro_nota_tentativa"),
    )

    op.create_table(
        "usuarios_admin",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ultimo_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_usuarios_admin_email"),
    )

    op.create_table(
        "auditorias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios_admin.id"), nullable=True),
        sa.Column("acao", sa.String(length=100), nullable=False),
        sa.Column("entidade", sa.String(length=100), nullable=False),
        sa.Column("entidade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dados_anteriores", postgresql.JSONB(), nullable=True),
        sa.Column("dados_novos", postgresql.JSONB(), nullable=True),
        sa.Column("ip", sa.String(length=60), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("auditorias")
    op.drop_table("usuarios_admin")
    op.drop_table("execucoes_cadastro")
    op.drop_table("processamentos_nota")
    op.drop_table("consentimentos")
    op.drop_index("ix_submissoes_nota_status", table_name="submissoes_nota")
    op.drop_table("submissoes_nota")
    op.drop_table("arquivos_importados")
    op.drop_table("mensagens_whatsapp")
    op.drop_index("ix_notas_fiscais_status", table_name="notas_fiscais")
    op.drop_index("ix_notas_fiscais_chave", table_name="notas_fiscais")
    op.drop_table("notas_fiscais")
    op.drop_index("ix_pessoas_telefone", table_name="pessoas")
    op.drop_table("pessoas")
