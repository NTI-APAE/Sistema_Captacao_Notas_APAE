from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.pessoa import Pessoa
from app.models.pessoa_model import PessoaModel


class PessoaMapper:
    @staticmethod
    def to_domain(model: PessoaModel) -> Pessoa:
        return Pessoa(
            id=model.id,
            telefone=model.telefone,
            nome=model.nome,
            ativo=model.ativo,
            criado_em=model.criado_em,
            atualizado_em=model.atualizado_em,
        )

    @staticmethod
    def to_model(entity: Pessoa) -> PessoaModel:
        return PessoaModel(
            id=entity.id,
            telefone=entity.telefone,
            nome=entity.nome,
            ativo=entity.ativo,
            criado_em=entity.criado_em,
            atualizado_em=entity.atualizado_em,
        )


class SQLAlchemyPessoaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def buscar_por_id(self, pessoa_id: UUID) -> Pessoa | None:
        model = self._session.get(PessoaModel, pessoa_id)
        return PessoaMapper.to_domain(model) if model else None

    def buscar_por_telefone(self, telefone: str) -> Pessoa | None:
        model = self._session.scalar(
            select(PessoaModel).where(PessoaModel.telefone == telefone),
        )
        return PessoaMapper.to_domain(model) if model else None

    def adicionar(self, pessoa: Pessoa) -> None:
        self._session.add(PessoaMapper.to_model(pessoa))
