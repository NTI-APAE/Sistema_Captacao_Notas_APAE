from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.submissao_nota import SubmissaoNota
from app.domain.enums.origem_submissao import OrigemSubmissao
from app.domain.enums.submissao_status import SubmissaoStatus
from app.models.submissao_nota_model import (
    SubmissaoNotaModel,
)


class SubmissaoNotaMapper:
    @staticmethod
    def to_domain(model: SubmissaoNotaModel) -> SubmissaoNota:
        return SubmissaoNota(
            id=model.id,
            pessoa_id=model.pessoa_id,
            mensagem_whatsapp_id=model.mensagem_whatsapp_id,
            arquivo_importado_id=model.arquivo_importado_id,
            nota_fiscal_id=model.nota_fiscal_id,
            origem=OrigemSubmissao(model.origem),
            imagem_path=model.imagem_path,
            chave_extraida=model.chave_extraida,
            status=SubmissaoStatus(model.status),
            erro_codigo=model.erro_codigo,
            erro_mensagem=model.erro_mensagem,
            data_recebimento=model.data_recebimento,
            criado_em=model.criado_em,
        )

    @staticmethod
    def to_model(entity: SubmissaoNota) -> SubmissaoNotaModel:
        return SubmissaoNotaModel(
            id=entity.id,
            pessoa_id=entity.pessoa_id,
            mensagem_whatsapp_id=entity.mensagem_whatsapp_id,
            arquivo_importado_id=entity.arquivo_importado_id,
            nota_fiscal_id=entity.nota_fiscal_id,
            origem=entity.origem.value,
            imagem_path=entity.imagem_path,
            chave_extraida=entity.chave_extraida,
            status=entity.status.value,
            erro_codigo=entity.erro_codigo,
            erro_mensagem=entity.erro_mensagem,
            data_recebimento=entity.data_recebimento,
            criado_em=entity.criado_em,
        )


class SQLAlchemySubmissaoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def buscar_por_id(self, submissao_id: UUID) -> SubmissaoNota | None:
        model = self._session.get(SubmissaoNotaModel, submissao_id)
        return SubmissaoNotaMapper.to_domain(model) if model else None

    def adicionar(self, submissao: SubmissaoNota) -> None:
        self._session.add(SubmissaoNotaMapper.to_model(submissao))

    def listar_por_nota(self, nota_id: UUID) -> list[SubmissaoNota]:
        models = self._session.scalars(
            select(SubmissaoNotaModel)
            .where(SubmissaoNotaModel.nota_fiscal_id == nota_id)
            .order_by(SubmissaoNotaModel.criado_em.asc()),
        ).all()
        return [SubmissaoNotaMapper.to_domain(model) for model in models]

    def listar_por_pessoa(self, pessoa_id: UUID) -> list[SubmissaoNota]:
        models = self._session.scalars(
            select(SubmissaoNotaModel)
            .where(SubmissaoNotaModel.pessoa_id == pessoa_id)
            .order_by(SubmissaoNotaModel.criado_em.asc()),
        ).all()
        return [SubmissaoNotaMapper.to_domain(model) for model in models]
