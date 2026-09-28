import logging
from datetime import timedelta

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.enums.execucao_status import ExecucaoStatus
from app.domain.exceptions.execucao_nao_encontrada_exception import (
    ExecucaoNaoEncontradaException,
)
from app.domain.exceptions.nota_nao_encontrada_exception import (
    NotaNaoEncontradaException,
)
from app.domain.time import utc_now
from app.repositories.contracts import Transaction
from app.schemas.execucao_cadastro_output import ExecucaoCadastroOutput
from app.schemas.worker_output import (
    ObterProximaNotaOutput,
    WorkerExecucaoOutput,
)


class ObterProximaNotaParaProcessamentoService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work
        self._logger = logging.getLogger(__name__)

    def execute(self) -> ObterProximaNotaOutput | None:
        with self._unit_of_work as uow:
            nota = uow.notas.obter_proxima_para_processamento()
            if nota is None:
                self._logger.info(
                    "fila de notas vazia",
                    extra={"event": "worker_empty"},
                )
                return None

            tentativa = uow.execucoes.obter_ultima_tentativa(nota.id) + 1
            execucao = ExecucaoCadastro(
                nota_fiscal_id=nota.id,
                tentativa=tentativa,
                status=ExecucaoStatus.EM_EXECUCAO,
                iniciado_em=utc_now(),
            )
            nota.iniciar_cadastro()
            uow.notas.salvar(nota)
            uow.execucoes.adicionar(execucao)
            uow.commit()

        self._logger.info(
            "worker reservou nota",
            extra={
                "event": "worker_claim",
                "nota_id": str(nota.id),
                "execucao_id": str(execucao.id),
                "tentativa": tentativa,
            },
        )
        return ObterProximaNotaOutput(
            nota_id=nota.id,
            execucao_id=execucao.id,
            chave=nota.chave,
            tentativa=tentativa,
        )


class ConsultarExecucaoWorkerService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, execucao_id) -> WorkerExecucaoOutput:
        with self._unit_of_work as uow:
            execucao = uow.execucoes.buscar_por_id(execucao_id)
            if execucao is None:
                raise ExecucaoNaoEncontradaException(execucao_id)
            return WorkerExecucaoOutput(
                execucao_id=execucao.id,
                nota_id=execucao.nota_fiscal_id,
                tentativa=execucao.tentativa,
                status=execucao.status,
                iniciado_em=execucao.iniciado_em,
                finalizado_em=execucao.finalizado_em,
            )


class RecuperarExecucoesExpiradasService:
    def __init__(
        self,
        unit_of_work: Transaction,
        timeout_minutes: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._timeout_minutes = timeout_minutes

    def execute(self) -> list[ExecucaoCadastroOutput]:
        limite = utc_now() - timedelta(minutes=self._timeout_minutes)
        recuperadas: list[ExecucaoCadastroOutput] = []
        with self._unit_of_work as uow:
            execucoes = uow.execucoes.listar_expiradas_em_execucao(limite)
            for execucao in execucoes:
                nota = uow.notas.buscar_por_id(execucao.nota_fiscal_id)
                if nota is None:
                    raise NotaNaoEncontradaException(execucao.nota_fiscal_id)
                mensagem = "Execucao expirada por timeout"
                agora = utc_now()
                execucao.expirar(mensagem, agora)
                nota.marcar_timeout_cadastro(mensagem)
                uow.execucoes.salvar(execucao)
                uow.notas.salvar(nota)
                recuperadas.append(ExecucaoCadastroOutput.from_domain(execucao))
            uow.commit()
        return recuperadas
