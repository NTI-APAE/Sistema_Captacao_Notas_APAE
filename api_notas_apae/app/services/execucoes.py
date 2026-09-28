import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.enums.execucao_status import ExecucaoStatus
from app.domain.enums.nota_status import NotaStatus
from app.domain.exceptions.execucao_nao_encontrada_exception import (
    ExecucaoNaoEncontradaException,
)
from app.domain.exceptions.nota_nao_encontrada_exception import (
    NotaNaoEncontradaException,
)
from app.domain.exceptions.transicao_status_invalida_exception import (
    TransicaoStatusInvalidaException,
)
from app.domain.time import utc_now
from app.repositories.contracts import Transaction
from app.schemas.execucao_cadastro_input import (
    RegistrarResultadoCadastroInput,
)
from app.schemas.execucao_cadastro_output import ExecucaoCadastroOutput


class IniciarExecucaoCadastroService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work
        self._logger = logging.getLogger(__name__)

    def execute(self, nota_id: UUID) -> ExecucaoCadastroOutput:
        with self._unit_of_work as uow:
            nota = uow.notas.buscar_por_id(nota_id)
            if nota is None:
                raise NotaNaoEncontradaException(nota_id)

            nota.iniciar_cadastro()
            tentativa = uow.execucoes.obter_ultima_tentativa(nota_id) + 1
            execucao = ExecucaoCadastro(
                nota_fiscal_id=nota.id,
                tentativa=tentativa,
                status=ExecucaoStatus.EM_EXECUCAO,
                iniciado_em=utc_now(),
            )
            uow.notas.salvar(nota)
            uow.execucoes.adicionar(execucao)
            uow.commit()
            self._logger.info(
                "execucao de cadastro iniciada",
                extra={
                    "nota_id": str(nota.id),
                    "execucao_id": str(execucao.id),
                    "resultado": "em_execucao",
                },
            )
            return ExecucaoCadastroOutput.from_domain(execucao)


class RegistrarResultadoCadastroService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work
        self._logger = logging.getLogger(__name__)

    def execute(
        self,
        data: RegistrarResultadoCadastroInput,
    ) -> ExecucaoCadastroOutput:
        with self._unit_of_work as uow:
            execucao = uow.execucoes.buscar_por_id(data.execucao_id)
            if execucao is None:
                raise ExecucaoNaoEncontradaException(data.execucao_id)
            if data.nota_id is not None and execucao.nota_fiscal_id != data.nota_id:
                raise ExecucaoNaoEncontradaException(data.execucao_id)

            nota = uow.notas.buscar_por_id(execucao.nota_fiscal_id)
            if nota is None:
                raise NotaNaoEncontradaException(execucao.nota_fiscal_id)

            agora = utc_now()
            tempo_segundos = self._tempo_execucao(execucao, data, agora)
            if data.status == ExecucaoStatus.SUCESSO:
                execucao.marcar_sucesso(
                    data.mensagem,
                    data.valor,
                    data.data_emissao,
                    tempo_segundos,
                    agora,
                )
                if nota.status != NotaStatus.CADASTRADA:
                    nota.marcar_cadastrada(data.valor, data.data_emissao, agora)
                    nota.mensagem_status = data.mensagem
            elif data.status == ExecucaoStatus.ERRO:
                execucao.marcar_erro(data.mensagem, tempo_segundos, agora)
                if nota.status != NotaStatus.ERRO_CADASTRO:
                    nota.marcar_erro_cadastro(data.mensagem)
            elif data.status == ExecucaoStatus.AGUARDANDO_CAPTCHA:
                execucao.aguardar_captcha(data.mensagem)
                nota.marcar_aguardando_captcha(data.mensagem)
            elif data.status == ExecucaoStatus.PAUSADA:
                execucao.pausar(data.mensagem)
                nota.pausar(data.mensagem)
            else:
                raise TransicaoStatusInvalidaException(
                    execucao.status.value,
                    data.status.value,
                )

            uow.notas.salvar(nota)
            uow.execucoes.salvar(execucao)
            uow.commit()
            self._logger.info(
                "resultado de cadastro registrado",
                extra={
                    "nota_id": str(nota.id),
                    "execucao_id": str(execucao.id),
                    "resultado": data.status.value,
                },
            )
            return ExecucaoCadastroOutput.from_domain(execucao)

    def _tempo_execucao(
        self,
        execucao: ExecucaoCadastro,
        data: RegistrarResultadoCadastroInput,
        finalizado_em: datetime,
    ) -> Decimal | None:
        if data.tempo_segundos is not None:
            return data.tempo_segundos
        if execucao.iniciado_em is None:
            return None
        iniciado_em = execucao.iniciado_em
        if iniciado_em.tzinfo is None and finalizado_em.tzinfo is not None:
            finalizado_em = finalizado_em.replace(tzinfo=None)
        if iniciado_em.tzinfo is not None and finalizado_em.tzinfo is None:
            iniciado_em = iniciado_em.replace(tzinfo=None)
        return Decimal(
            str((finalizado_em - iniciado_em).total_seconds()),
        )


class ListarExecucoesCadastroService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, nota_id: UUID) -> list[ExecucaoCadastroOutput]:
        with self._unit_of_work as uow:
            if uow.notas.buscar_por_id(nota_id) is None:
                raise NotaNaoEncontradaException(nota_id)
            return [
                ExecucaoCadastroOutput.from_domain(execucao)
                for execucao in uow.execucoes.listar_por_nota(nota_id)
            ]
