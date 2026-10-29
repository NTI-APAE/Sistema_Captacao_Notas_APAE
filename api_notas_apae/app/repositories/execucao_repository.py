from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.enums.execucao_fase import ExecucaoFase
from app.domain.enums.execucao_status import ExecucaoStatus
from app.models.execucao_cadastro_model import ExecucaoCadastroModel
from app.models.nota_fiscal_model import NotaFiscalModel


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
            worker_id=model.worker_id,
            ultimo_heartbeat_em=model.ultimo_heartbeat_em,
            lease_expira_em=model.lease_expira_em,
            fase_portal=ExecucaoFase(model.fase_portal),
            efeito_externo_iniciado_em=model.efeito_externo_iniciado_em,
            motivo_recuperacao=model.motivo_recuperacao,
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
            worker_id=entity.worker_id,
            ultimo_heartbeat_em=entity.ultimo_heartbeat_em,
            lease_expira_em=entity.lease_expira_em,
            fase_portal=entity.fase_portal.value,
            efeito_externo_iniciado_em=entity.efeito_externo_iniciado_em,
            motivo_recuperacao=entity.motivo_recuperacao,
        )


class SQLAlchemyExecucaoCadastroRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def buscar_por_id(self, execucao_id: UUID) -> ExecucaoCadastro | None:
        model = self._session.get(ExecucaoCadastroModel, execucao_id)
        return ExecucaoCadastroMapper.to_domain(model) if model else None

    def buscar_por_id_com_lock(self, execucao_id: UUID) -> ExecucaoCadastro | None:
        nota_id = self._session.scalar(
            select(ExecucaoCadastroModel.nota_fiscal_id).where(
                ExecucaoCadastroModel.id == execucao_id,
            ),
        )
        if nota_id is None:
            return None
        self._session.get(NotaFiscalModel, nota_id, with_for_update=True)
        model = self._session.get(
            ExecucaoCadastroModel,
            execucao_id,
            with_for_update=True,
        )
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
        model.worker_id = execucao.worker_id
        model.ultimo_heartbeat_em = execucao.ultimo_heartbeat_em
        model.lease_expira_em = execucao.lease_expira_em
        model.fase_portal = execucao.fase_portal.value
        model.efeito_externo_iniciado_em = execucao.efeito_externo_iniciado_em
        model.motivo_recuperacao = execucao.motivo_recuperacao

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

    def listar_abandonadas_com_lock(
        self, agora, limite_legacy
    ) -> list[ExecucaoCadastro]:
        candidate_ids = self._session.scalars(
            select(ExecucaoCadastroModel.id)
            .join(
                NotaFiscalModel,
                NotaFiscalModel.id == ExecucaoCadastroModel.nota_fiscal_id,
            )
            .where(
                ExecucaoCadastroModel.status.in_(
                    [
                        ExecucaoStatus.EM_EXECUCAO.value,
                        ExecucaoStatus.AGUARDANDO_CAPTCHA.value,
                        ExecucaoStatus.PAUSADA.value,
                    ],
                ),
            )
            .where(
                (ExecucaoCadastroModel.lease_expira_em < agora)
                | (
                    ExecucaoCadastroModel.lease_expira_em.is_(None)
                    & (ExecucaoCadastroModel.iniciado_em < limite_legacy)
                ),
            )
            .order_by(NotaFiscalModel.criado_em.asc())
            .with_for_update(of=NotaFiscalModel, skip_locked=True),
        ).all()
        if not candidate_ids:
            return []
        models = self._session.scalars(
            select(ExecucaoCadastroModel)
            .where(ExecucaoCadastroModel.id.in_(candidate_ids))
            .with_for_update(),
        ).all()
        return [ExecucaoCadastroMapper.to_domain(model) for model in models]

    def salvar_heartbeat(
        self,
        execucao_id: UUID,
        *,
        worker_id: str,
        agora,
        lease_expira_em,
    ) -> ExecucaoCadastro | None:
        model = self._session.scalar(
            select(ExecucaoCadastroModel)
            .where(ExecucaoCadastroModel.id == execucao_id)
            .with_for_update(),
        )
        if model is None:
            return None
        if model.worker_id not in {None, worker_id}:
            return ExecucaoCadastroMapper.to_domain(model)
        model.worker_id = worker_id
        model.ultimo_heartbeat_em = agora
        model.lease_expira_em = lease_expira_em
        return ExecucaoCadastroMapper.to_domain(model)

    def listar_reconciliacoes(self) -> list[ExecucaoCadastro]:
        models = self._session.scalars(
            select(ExecucaoCadastroModel)
            .where(
                ExecucaoCadastroModel.status
                == ExecucaoStatus.RESULTADO_DESCONHECIDO.value,
            )
            .order_by(ExecucaoCadastroModel.criado_em.asc()),
        ).all()
        return [ExecucaoCadastroMapper.to_domain(model) for model in models]
