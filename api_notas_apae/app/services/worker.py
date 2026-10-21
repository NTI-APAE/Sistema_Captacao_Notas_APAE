import logging
from datetime import timedelta
from uuid import UUID

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.enums.execucao_fase import ExecucaoFase
from app.domain.enums.execucao_status import ExecucaoStatus
from app.domain.enums.nota_status import NotaStatus
from app.domain.exceptions.execucao_nao_encontrada_exception import (
    ExecucaoNaoEncontradaException,
)
from app.domain.exceptions.nota_nao_encontrada_exception import (
    NotaNaoEncontradaException,
)
from app.domain.exceptions.resultado_execucao_conflitante_exception import (
    ResultadoExecucaoConflitanteException,
)
from app.domain.time import utc_now
from app.repositories.contracts import Transaction
from app.schemas.execucao_cadastro_output import ExecucaoCadastroOutput
from app.schemas.worker_output import (
    ObterProximaNotaOutput,
    WorkerExecucaoOutput,
)


class ObterProximaNotaParaProcessamentoService:
    def __init__(
        self,
        unit_of_work: Transaction,
        max_attempts: int | None = None,
        lease_timeout_seconds: int = 120,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._max_attempts = max_attempts
        self._lease_timeout_seconds = lease_timeout_seconds
        self._logger = logging.getLogger(__name__)

    def execute(
        self, worker_id: str = "legacy-worker"
    ) -> ObterProximaNotaOutput | None:
        with self._unit_of_work as uow:
            if self._max_attempts is None:
                nota = uow.notas.obter_proxima_para_processamento()
            else:
                nota = uow.notas.obter_proxima_para_processamento(self._max_attempts)
            if nota is None:
                self._logger.info(
                    "fila de notas vazia",
                    extra={"event": "worker_empty"},
                )
                return None

            agora = utc_now()
            tentativa = uow.execucoes.obter_ultima_tentativa(nota.id) + 1
            execucao = ExecucaoCadastro(
                nota_fiscal_id=nota.id,
                tentativa=tentativa,
                status=ExecucaoStatus.EM_EXECUCAO,
                iniciado_em=agora,
                worker_id=worker_id,
                ultimo_heartbeat_em=agora,
                lease_expira_em=agora + timedelta(seconds=self._lease_timeout_seconds),
                fase_portal=ExecucaoFase.RESERVADA,
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
            worker_id=execucao.worker_id or worker_id,
            lease_expira_em=execucao.lease_expira_em,
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
                ultimo_heartbeat_em=execucao.ultimo_heartbeat_em,
                lease_expira_em=execucao.lease_expira_em,
                fase_portal=execucao.fase_portal.value,
            )


class RegistrarHeartbeatWorkerService:
    def __init__(
        self,
        unit_of_work: Transaction,
        lease_timeout_seconds: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._lease_timeout_seconds = lease_timeout_seconds

    def execute(
        self,
        execucao_id: UUID,
        *,
        worker_id: str,
        fase: ExecucaoFase | None = None,
        mensagem: str | None = None,
    ) -> WorkerExecucaoOutput:
        agora = utc_now()
        with self._unit_of_work as uow:
            execucao = uow.execucoes.buscar_por_id_com_lock(execucao_id)
            if execucao is None:
                raise ExecucaoNaoEncontradaException(execucao_id)
            if execucao.lease_expira_em and execucao.lease_expira_em <= agora:
                raise ResultadoExecucaoConflitanteException()
            if execucao.worker_id not in {None, worker_id}:
                raise ResultadoExecucaoConflitanteException()

            nota = uow.notas.buscar_por_id(execucao.nota_fiscal_id)
            if nota is None:
                raise NotaNaoEncontradaException(execucao.nota_fiscal_id)
            if fase == ExecucaoFase.PORTAL_INICIADO:
                execucao.marcar_portal_iniciado(agora)
            elif fase == ExecucaoFase.AGUARDANDO_CAPTCHA:
                execucao.aguardar_captcha(mensagem)
                if nota.status != NotaStatus.AGUARDANDO_CAPTCHA:
                    nota.marcar_aguardando_captcha(mensagem)
            elif fase == ExecucaoFase.PAUSADA:
                execucao.pausar(mensagem)
                if nota.status != NotaStatus.PAUSADA:
                    nota.pausar(mensagem)
            elif fase == ExecucaoFase.RESULTADO_ENVIANDO:
                execucao.marcar_resultado_enviando(agora)

            execucao.renovar_lease(
                worker_id=worker_id,
                agora=agora,
                lease_expira_em=agora + timedelta(seconds=self._lease_timeout_seconds),
            )
            uow.execucoes.salvar(execucao)
            uow.notas.salvar(nota)
            uow.commit()
            return WorkerExecucaoOutput(
                execucao_id=execucao.id,
                nota_id=execucao.nota_fiscal_id,
                tentativa=execucao.tentativa,
                status=execucao.status,
                iniciado_em=execucao.iniciado_em,
                finalizado_em=execucao.finalizado_em,
                ultimo_heartbeat_em=execucao.ultimo_heartbeat_em,
                lease_expira_em=execucao.lease_expira_em,
                fase_portal=execucao.fase_portal.value,
            )


class RetomarExecucaoWorkerService:
    def __init__(self, unit_of_work: Transaction, lease_timeout_seconds: int) -> None:
        self._unit_of_work = unit_of_work
        self._lease_timeout_seconds = lease_timeout_seconds

    def execute(self, execucao_id: UUID, *, worker_id: str) -> WorkerExecucaoOutput:
        agora = utc_now()
        with self._unit_of_work as uow:
            execucao = uow.execucoes.buscar_por_id_com_lock(execucao_id)
            if execucao is None:
                raise ExecucaoNaoEncontradaException(execucao_id)
            if execucao.worker_id not in {None, worker_id}:
                raise ResultadoExecucaoConflitanteException()
            if execucao.lease_expira_em and execucao.lease_expira_em <= agora:
                raise ResultadoExecucaoConflitanteException()
            nota = uow.notas.buscar_por_id(execucao.nota_fiscal_id)
            if nota is None:
                raise NotaNaoEncontradaException(execucao.nota_fiscal_id)
            execucao.retomar(agora)
            if nota.status in {NotaStatus.AGUARDANDO_CAPTCHA, NotaStatus.PAUSADA}:
                nota.retomar_cadastro()
            execucao.renovar_lease(
                worker_id=worker_id,
                agora=agora,
                lease_expira_em=agora + timedelta(seconds=self._lease_timeout_seconds),
            )
            uow.execucoes.salvar(execucao)
            uow.notas.salvar(nota)
            uow.commit()
            return WorkerExecucaoOutput(
                execucao_id=execucao.id,
                nota_id=execucao.nota_fiscal_id,
                tentativa=execucao.tentativa,
                status=execucao.status,
                iniciado_em=execucao.iniciado_em,
                finalizado_em=execucao.finalizado_em,
                ultimo_heartbeat_em=execucao.ultimo_heartbeat_em,
                lease_expira_em=execucao.lease_expira_em,
                fase_portal=execucao.fase_portal.value,
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
        agora = utc_now()
        limite = agora - timedelta(minutes=self._timeout_minutes)
        recuperadas: list[ExecucaoCadastroOutput] = []
        with self._unit_of_work as uow:
            execucoes = uow.execucoes.listar_abandonadas_com_lock(agora, limite)
            for execucao in execucoes:
                nota = uow.notas.buscar_por_id(execucao.nota_fiscal_id)
                if nota is None:
                    raise NotaNaoEncontradaException(execucao.nota_fiscal_id)
                if (
                    execucao.status == ExecucaoStatus.EM_EXECUCAO
                    and execucao.fase_portal == ExecucaoFase.RESERVADA
                ):
                    mensagem = "Execucao abandonada antes do inicio do portal"
                    execucao.expirar(mensagem, agora)
                    nota.marcar_timeout_cadastro(mensagem)
                    nota.reprocessar()
                else:
                    mensagem = (
                        "Resultado desconhecido: a execucao expirou depois de iniciar "
                        "ou durante uma pausa/CAPTCHA"
                    )
                    execucao.marcar_resultado_desconhecido(mensagem, agora)
                    if nota.status != NotaStatus.RESULTADO_DESCONHECIDO:
                        nota.marcar_resultado_desconhecido(mensagem)
                uow.execucoes.salvar(execucao)
                uow.notas.salvar(nota)
                recuperadas.append(ExecucaoCadastroOutput.from_domain(execucao))
            uow.commit()
        return recuperadas


class ListarExecucoesReconciliacaoService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def execute(self) -> list[ExecucaoCadastroOutput]:
        with self._unit_of_work as uow:
            return [
                ExecucaoCadastroOutput.from_domain(execucao)
                for execucao in uow.execucoes.listar_reconciliacoes()
            ]
