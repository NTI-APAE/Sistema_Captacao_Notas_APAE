from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.enums.nota_status import NotaStatus
from app.models.nota_fiscal_model import (
    NotaFiscalModel,
)
from app.models.pessoa_model import PessoaModel
from app.models.submissao_nota_model import (
    SubmissaoNotaModel,
)
from app.schemas.pagination import ListarNotasFiltro, PaginatedOutput


class NotaFiscalMapper:
    @staticmethod
    def to_domain(model: NotaFiscalModel) -> NotaFiscal:
        return NotaFiscal(
            id=model.id,
            chave=model.chave,
            status=NotaStatus(model.status),
            mensagem_status=model.mensagem_status,
            valor=model.valor,
            data_emissao=model.data_emissao,
            data_cadastro=model.data_cadastro,
            criado_em=model.criado_em,
            atualizado_em=model.atualizado_em,
        )

    @staticmethod
    def to_model(entity: NotaFiscal) -> NotaFiscalModel:
        return NotaFiscalModel(
            id=entity.id,
            chave=entity.chave,
            status=entity.status.value,
            mensagem_status=entity.mensagem_status,
            valor=entity.valor,
            data_emissao=entity.data_emissao,
            data_cadastro=entity.data_cadastro,
            criado_em=entity.criado_em,
            atualizado_em=entity.atualizado_em,
        )


class SQLAlchemyNotaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def buscar_por_id(self, nota_id: UUID) -> NotaFiscal | None:
        model = self._session.get(NotaFiscalModel, nota_id)
        return NotaFiscalMapper.to_domain(model) if model else None

    def buscar_por_chave(self, chave: str) -> NotaFiscal | None:
        model = self._session.scalar(
            select(NotaFiscalModel).where(NotaFiscalModel.chave == chave),
        )
        return NotaFiscalMapper.to_domain(model) if model else None

    def adicionar(self, nota: NotaFiscal) -> None:
        self._session.add(NotaFiscalMapper.to_model(nota))

    def salvar(self, nota: NotaFiscal) -> None:
        model = self._session.get(NotaFiscalModel, nota.id)
        if model is None:
            self.adicionar(nota)
            return
        model.chave = nota.chave
        model.status = nota.status.value
        model.mensagem_status = nota.mensagem_status
        model.valor = nota.valor
        model.data_emissao = nota.data_emissao
        model.data_cadastro = nota.data_cadastro
        model.atualizado_em = nota.atualizado_em

    def listar(self, filtro: ListarNotasFiltro) -> PaginatedOutput[NotaFiscal]:
        statement = self._aplicar_filtros(select(NotaFiscalModel), filtro)
        count_statement = self._aplicar_filtros(select(NotaFiscalModel.id), filtro)
        total = len(self._session.scalars(count_statement).all())
        models = self._session.scalars(
            statement.order_by(NotaFiscalModel.criado_em.desc())
            .limit(filtro.size)
            .offset(filtro.offset),
        ).all()
        return PaginatedOutput(
            items=[NotaFiscalMapper.to_domain(model) for model in models],
            page=filtro.page,
            size=filtro.size,
            total=total,
        )

    def listar_por_pessoa_unicas(self, pessoa_id: UUID) -> list[NotaFiscal]:
        models = self._session.scalars(
            select(NotaFiscalModel)
            .join(SubmissaoNotaModel)
            .where(SubmissaoNotaModel.pessoa_id == pessoa_id)
            .distinct()
            .order_by(NotaFiscalModel.criado_em.desc()),
        ).all()
        return [NotaFiscalMapper.to_domain(model) for model in models]

    def obter_proxima_para_processamento(self) -> NotaFiscal | None:
        self._acquire_sqlite_claim_lock()
        model = self._session.scalar(
            select(NotaFiscalModel)
            .where(NotaFiscalModel.status == NotaStatus.PENDENTE.value)
            .order_by(NotaFiscalModel.criado_em.asc())
            .with_for_update(skip_locked=True)
            .limit(1),
        )
        return NotaFiscalMapper.to_domain(model) if model else None

    def _acquire_sqlite_claim_lock(self) -> None:
        if self._session.bind is None or self._session.bind.dialect.name != "sqlite":
            return
        self._session.execute(text("BEGIN IMMEDIATE"))

    def _aplicar_filtros(self, statement, filtro: ListarNotasFiltro):
        if filtro.telefone:
            statement = statement.join(SubmissaoNotaModel).join(
                SubmissaoNotaModel.pessoa,
            )
            statement = statement.where(PessoaModel.telefone == filtro.telefone)
        if filtro.status:
            statement = statement.where(NotaFiscalModel.status == filtro.status.value)
        if filtro.chave:
            statement = statement.where(NotaFiscalModel.chave == filtro.chave)
        if filtro.data_inicial:
            statement = statement.where(
                NotaFiscalModel.data_emissao >= filtro.data_inicial,
            )
        if filtro.data_final:
            statement = statement.where(
                NotaFiscalModel.data_emissao <= filtro.data_final,
            )
        return statement.distinct()
