from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

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

    def aguardar_captcha(self, mensagem: str | None) -> None:
        if self.status == ExecucaoStatus.AGUARDANDO_CAPTCHA:
            self.mensagem = mensagem
            return
        self._garantir_pode_receber(ExecucaoStatus.AGUARDANDO_CAPTCHA)
        self.status = ExecucaoStatus.AGUARDANDO_CAPTCHA
        self.mensagem = mensagem
        self.finalizado_em = None

    def pausar(self, mensagem: str | None) -> None:
        if self.status == ExecucaoStatus.PAUSADA:
            self.mensagem = mensagem
            return
        self._garantir_pode_receber(ExecucaoStatus.PAUSADA)
        self.status = ExecucaoStatus.PAUSADA
        self.mensagem = mensagem
        self.finalizado_em = None

    def expirar(self, mensagem: str, finalizado_em: datetime) -> None:
        self._garantir_pode_receber(ExecucaoStatus.ERRO)
        self.status = ExecucaoStatus.ERRO
        self.mensagem = mensagem
        self.finalizado_em = finalizado_em

    def _garantir_pode_receber(self, destino: ExecucaoStatus) -> None:
        if self.status in {ExecucaoStatus.SUCESSO, ExecucaoStatus.ERRO}:
            raise ResultadoExecucaoConflitanteException()
        if self.status not in {
            ExecucaoStatus.EM_EXECUCAO,
            ExecucaoStatus.AGUARDANDO_CAPTCHA,
            ExecucaoStatus.PAUSADA,
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
        if destino != ExecucaoStatus.SUCESSO:
            return True
        return self.valor_obtido == valor and self.data_emissao_obtida == data_emissao
