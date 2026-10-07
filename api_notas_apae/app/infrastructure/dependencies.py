from typing import Annotated

from fastapi import Depends

from app.infrastructure.config import get_settings
from app.repositories.contracts import Transaction
from app.repositories.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from app.services.execucoes import RegistrarResultadoCadastroService
from app.services.notas import ConsultarNotaService, ListarNotasService
from app.services.resumos_leitor import RegistrarResumoOperacaoLeitorService
from app.services.worker import (
    ConsultarExecucaoWorkerService,
    ObterProximaNotaParaProcessamentoService,
    RecuperarExecucoesExpiradasService,
)


def get_unit_of_work() -> Transaction:
    return SQLAlchemyUnitOfWork()


def get_consultar_nota_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ConsultarNotaService:
    return ConsultarNotaService(unit_of_work=unit_of_work)


def get_listar_notas_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ListarNotasService:
    return ListarNotasService(unit_of_work=unit_of_work)


def get_registrar_resultado_cadastro_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> RegistrarResultadoCadastroService:
    return RegistrarResultadoCadastroService(unit_of_work=unit_of_work)


def get_registrar_resumo_operacao_leitor_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> RegistrarResumoOperacaoLeitorService:
    return RegistrarResumoOperacaoLeitorService(unit_of_work=unit_of_work)


def get_obter_proxima_nota_worker_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ObterProximaNotaParaProcessamentoService:
    return ObterProximaNotaParaProcessamentoService(
        unit_of_work=unit_of_work,
        max_attempts=get_settings().worker_max_attempts,
    )


def get_consultar_execucao_worker_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ConsultarExecucaoWorkerService:
    return ConsultarExecucaoWorkerService(unit_of_work=unit_of_work)


def get_recuperar_execucoes_expiradas_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> RecuperarExecucoesExpiradasService:
    return RecuperarExecucoesExpiradasService(
        unit_of_work=unit_of_work,
        timeout_minutes=get_settings().worker_execution_timeout_minutes,
    )
