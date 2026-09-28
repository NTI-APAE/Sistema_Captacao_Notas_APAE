from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.enums.execucao_status import ExecucaoStatus
from app.models.execucao_cadastro_model import ExecucaoCadastroModel


class ExecucaoCadastroMapper:
    @staticmethod
    def to_domain(model: ExecucaoCadastroModel) -> ExecucaoCadastro:
        return ExecucaoCadastro(
            id=model.id,
            nota_fiscal_id=model.nota_fiscal_id,
            tentativa=model.tentativa,
            status=ExecucaoStatus(model.status),
            mensagem=model.mensagem,
            workflow_execution_id=model.workflow_execution_id,
            valor_obtido=model.valor_obtido,
            data_emissao_obtida=model.data_emissao_obtida,
            tempo_segundos=model.tempo_segundos,
            iniciado_em=model.iniciado_em,
            finalizado_em=model.finalizado_em,
            criado_em=model.criado_em,
        )

    @staticmethod
    def to_model(entity: ExecucaoCadastro) -> ExecucaoCadastroModel:
        return ExecucaoCadastroModel(
            id=entity.id,
            nota_fiscal_id=entity.nota_fiscal_id,
            tentativa=entity.tentativa,
            status=entity.status.value,
            mensagem=entity.mensagem,
            workflow_execution_id=entity.workflow_execution_id,
            valor_obtido=entity.valor_obtido,
            data_emissao_obtida=entity.data_emissao_obtida,
            tempo_segundos=entity.tempo_segundos,
            iniciado_em=entity.iniciado_em,
            finalizado_em=entity.finalizado_em,
            criado_em=entity.criado_em,
        )


class SQLAlchemyExecucaoCadastroRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def buscar_por_id(self, execucao_id: UUID) -> ExecucaoCadastro | None:
        model = self._session.get(ExecucaoCadastroModel, execucao_id)
        return ExecucaoCadastroMapper.to_domain(model) if model else None

    def listar_por_nota(self, nota_id: UUID) -> list[ExecucaoCadastro]:
        models = self._session.scalars(
            select(ExecucaoCadastroModel)
            .where(ExecucaoCadastroModel.nota_fiscal_id == nota_id)
            .order_by(ExecucaoCadastroModel.tentativa.asc()),
        ).all()
        return [ExecucaoCadastroMapper.to_domain(model) for model in models]

    def obter_ultima_tentativa(self, nota_id: UUID) -> int:
        ultima = self._session.scalar(
            select(func.max(ExecucaoCadastroModel.tentativa)).where(
                ExecucaoCadastroModel.nota_fiscal_id == nota_id,
            ),
        )
        return int(ultima or 0)

    def adicionar(self, execucao: ExecucaoCadastro) -> None:
        self._session.add(ExecucaoCadastroMapper.to_model(execucao))

    def salvar(self, execucao: ExecucaoCadastro) -> None:
        model = self._session.get(ExecucaoCadastroModel, execucao.id)
        if model is None:
            self.adicionar(execucao)
            return
        model.status = execucao.status.value
        model.mensagem = execucao.mensagem
        model.workflow_execution_id = execucao.workflow_execution_id
        model.valor_obtido = execucao.valor_obtido
        model.data_emissao_obtida = execucao.data_emissao_obtida
        model.tempo_segundos = execucao.tempo_segundos
        model.iniciado_em = execucao.iniciado_em
        model.finalizado_em = execucao.finalizado_em

    def listar_expiradas_em_execucao(
        self,
        limite_iniciado_em,
    ) -> list[ExecucaoCadastro]:
        models = self._session.scalars(
            select(ExecucaoCadastroModel)
            .where(ExecucaoCadastroModel.status == ExecucaoStatus.EM_EXECUCAO.value)
            .where(ExecucaoCadastroModel.iniciado_em < limite_iniciado_em),
        ).all()
        return [ExecucaoCadastroMapper.to_domain(model) for model in models]
