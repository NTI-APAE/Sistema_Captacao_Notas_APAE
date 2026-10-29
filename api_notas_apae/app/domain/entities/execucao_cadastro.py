from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.enums.execucao_fase import ExecucaoFase
from app.domain.enums.execucao_status import ExecucaoStatus
from app.domain.exceptions.resultado_execucao_conflitante_exception import (
    ResultadoExecucaoConflitanteException,
)
from app.domain.exceptions.transicao_status_invalida_exception import (
    TransicaoStatusInvalidaException,
)
from app.domain.time import utc_now


@dataclass(slots=True)
class ExecucaoCadastro:
    nota_fiscal_id: UUID
    tentativa: int
    status: ExecucaoStatus
    id: UUID = field(default_factory=uuid4)
    mensagem: str | None = None
    workflow_execution_id: str | None = None
    valor_obtido: Decimal | None = None
    data_emissao_obtida: date | None = None
    tempo_segundos: Decimal | None = None
    iniciado_em: datetime | None = None
    finalizado_em: datetime | None = None
    criado_em: datetime = field(default_factory=utc_now)
    worker_id: str | None = None
    ultimo_heartbeat_em: datetime | None = None
    lease_expira_em: datetime | None = None
    fase_portal: ExecucaoFase = ExecucaoFase.RESERVADA
    efeito_externo_iniciado_em: datetime | None = None
    motivo_recuperacao: str | None = None

    def renovar_lease(
        self,
        *,
        worker_id: str,
        agora: datetime,
        lease_expira_em: datetime,
    ) -> None:
        if self.status in {
            ExecucaoStatus.SUCESSO,
            ExecucaoStatus.DUPLICADA,
            ExecucaoStatus.IGNORADA,
            ExecucaoStatus.ERRO,
            ExecucaoStatus.RESULTADO_DESCONHECIDO,
        }:
            raise ResultadoExecucaoConflitanteException()
        if self.worker_id is not None and self.worker_id != worker_id:
            raise ResultadoExecucaoConflitanteException()
        self.worker_id = worker_id
        self.ultimo_heartbeat_em = agora
        self.lease_expira_em = lease_expira_em

    def marcar_portal_iniciado(self, agora: datetime) -> None:
        self._garantir_pode_receber(ExecucaoStatus.EM_EXECUCAO)
        self.fase_portal = ExecucaoFase.PORTAL_INICIADO
        self.efeito_externo_iniciado_em = agora

    def marcar_resultado_enviando(self, agora: datetime) -> None:
        self._garantir_pode_receber(ExecucaoStatus.EM_EXECUCAO)
        self.fase_portal = ExecucaoFase.RESULTADO_ENVIANDO
        self.efeito_externo_iniciado_em = self.efeito_externo_iniciado_em or agora

    def retomar(self, agora: datetime) -> None:
        if self.status == ExecucaoStatus.RESULTADO_DESCONHECIDO:
            raise ResultadoExecucaoConflitanteException()
        if self.status not in {
            ExecucaoStatus.AGUARDANDO_CAPTCHA,
            ExecucaoStatus.PAUSADA,
        }:
            if self.status == ExecucaoStatus.EM_EXECUCAO:
                return
            self._garantir_pode_receber(ExecucaoStatus.EM_EXECUCAO)
        self.status = ExecucaoStatus.EM_EXECUCAO
        self.finalizado_em = None
        self.fase_portal = (
            ExecucaoFase.PORTAL_INICIADO
            if self.efeito_externo_iniciado_em is not None
            else ExecucaoFase.RESERVADA
        )
        self.ultimo_heartbeat_em = agora

    def marcar_resultado_desconhecido(self, mensagem: str, agora: datetime) -> None:
        if self.status == ExecucaoStatus.RESULTADO_DESCONHECIDO:
            self.mensagem = mensagem
            self.motivo_recuperacao = mensagem
            return
        self._garantir_pode_receber(ExecucaoStatus.RESULTADO_DESCONHECIDO)
        self.status = ExecucaoStatus.RESULTADO_DESCONHECIDO
        self.mensagem = mensagem
        self.motivo_recuperacao = mensagem
        self.finalizado_em = None
        self.lease_expira_em = agora

    def marcar_sucesso(
        self,
        mensagem: str | None,
        valor: Decimal | None,
        data_emissao: date | None,
        tempo_segundos: Decimal | None,
        finalizado_em: datetime,
    ) -> None:
        if self._resultado_repetido(
            ExecucaoStatus.SUCESSO,
            mensagem,
            valor,
            data_emissao,
        ):
            return
        self._garantir_pode_receber(ExecucaoStatus.SUCESSO)
        self.status = ExecucaoStatus.SUCESSO
        self.mensagem = mensagem
        self.valor_obtido = valor
        self.data_emissao_obtida = data_emissao
        self.tempo_segundos = tempo_segundos
        self.finalizado_em = finalizado_em

    def marcar_erro(
        self,
        mensagem: str | None,
        tempo_segundos: Decimal | None,
        finalizado_em: datetime,
    ) -> None:
        if self._resultado_repetido(
            ExecucaoStatus.ERRO,
            mensagem,
            None,
            None,
        ):
            return
        self._garantir_pode_receber(ExecucaoStatus.ERRO)
        self.status = ExecucaoStatus.ERRO
        self.mensagem = mensagem
        self.tempo_segundos = tempo_segundos
        self.finalizado_em = finalizado_em

    def marcar_duplicada(
        self,
        mensagem: str | None,
        valor: Decimal | None,
        data_emissao: date | None,
        tempo_segundos: Decimal | None,
        finalizado_em: datetime,
    ) -> None:
        if self._resultado_repetido(
            ExecucaoStatus.DUPLICADA, mensagem, valor, data_emissao
        ):
            return
        self._garantir_pode_receber(ExecucaoStatus.DUPLICADA)
        self.status = ExecucaoStatus.DUPLICADA
        self.mensagem = mensagem
        self.valor_obtido = valor
        self.data_emissao_obtida = data_emissao
        self.tempo_segundos = tempo_segundos
        self.finalizado_em = finalizado_em

    def marcar_ignorada(
        self,
        mensagem: str | None,
        valor: Decimal | None,
        data_emissao: date | None,
        tempo_segundos: Decimal | None,
        finalizado_em: datetime,
    ) -> None:
        if self._resultado_repetido(
            ExecucaoStatus.IGNORADA, mensagem, valor, data_emissao
        ):
            return
        self._garantir_pode_receber(ExecucaoStatus.IGNORADA)
        self.status = ExecucaoStatus.IGNORADA
        self.mensagem = mensagem
        self.valor_obtido = valor
        self.data_emissao_obtida = data_emissao
        self.tempo_segundos = tempo_segundos
        self.finalizado_em = finalizado_em

    def aguardar_captcha(self, mensagem: str | None) -> None:
        if self.status == ExecucaoStatus.AGUARDANDO_CAPTCHA:
            self.mensagem = mensagem
            return
        self._garantir_pode_receber(ExecucaoStatus.AGUARDANDO_CAPTCHA)
        self.status = ExecucaoStatus.AGUARDANDO_CAPTCHA
        self.mensagem = mensagem
        self.finalizado_em = None
        self.fase_portal = ExecucaoFase.AGUARDANDO_CAPTCHA

    def pausar(self, mensagem: str | None) -> None:
        if self.status == ExecucaoStatus.PAUSADA:
            self.mensagem = mensagem
            return
        self._garantir_pode_receber(ExecucaoStatus.PAUSADA)
        self.status = ExecucaoStatus.PAUSADA
        self.mensagem = mensagem
        self.finalizado_em = None
        self.fase_portal = ExecucaoFase.PAUSADA

    def expirar(self, mensagem: str, finalizado_em: datetime) -> None:
        self._garantir_pode_receber(ExecucaoStatus.ERRO)
        self.status = ExecucaoStatus.ERRO
        self.mensagem = mensagem
        self.finalizado_em = finalizado_em

    def _garantir_pode_receber(self, destino: ExecucaoStatus) -> None:
        if self.status in {
            ExecucaoStatus.SUCESSO,
            ExecucaoStatus.DUPLICADA,
            ExecucaoStatus.IGNORADA,
            ExecucaoStatus.ERRO,
        }:
            raise ResultadoExecucaoConflitanteException()
        if self.status not in {
            ExecucaoStatus.EM_EXECUCAO,
            ExecucaoStatus.AGUARDANDO_CAPTCHA,
            ExecucaoStatus.PAUSADA,
            ExecucaoStatus.RESULTADO_DESCONHECIDO,
        }:
            raise TransicaoStatusInvalidaException(self.status.value, destino.value)

    def _resultado_repetido(
        self,
        destino: ExecucaoStatus,
        mensagem: str | None,
        valor: Decimal | None,
        data_emissao: date | None,
    ) -> bool:
        if self.status != destino:
            if self.status in {ExecucaoStatus.SUCESSO, ExecucaoStatus.ERRO}:
                raise ResultadoExecucaoConflitanteException()
            return False
        if self.mensagem != mensagem:
            return False
        if destino not in {
            ExecucaoStatus.SUCESSO,
            ExecucaoStatus.DUPLICADA,
            ExecucaoStatus.IGNORADA,
        }:
            return True
        return self.valor_obtido == valor and self.data_emissao_obtida == data_emissao
