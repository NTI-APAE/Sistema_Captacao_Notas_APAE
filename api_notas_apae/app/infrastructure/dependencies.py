from typing import Annotated

from fastapi import Depends

from app.infrastructure.config import get_settings
from app.repositories.contracts import Transaction
from app.repositories.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from app.services.execucoes import (
    IniciarExecucaoCadastroService,
    ListarExecucoesCadastroService,
    RegistrarResultadoCadastroService,
)
from app.services.notas import (
    ConsultarNotaService,
    ListarNotasDaPessoaService,
    ListarNotasService,
    ListarSubmissoesDaNotaService,
    ReprocessarNotaService,
)
from app.services.pessoas import ConsultarPessoaService
from app.services.submissoes import RegistrarSubmissaoService
from app.services.worker import (
    ConsultarExecucaoWorkerService,
    ObterProximaNotaParaProcessamentoService,
    RecuperarExecucoesExpiradasService,
)


def get_unit_of_work() -> Transaction:
    return SQLAlchemyUnitOfWork()


def get_registrar_submissao_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> RegistrarSubmissaoService:
    return RegistrarSubmissaoService(unit_of_work=unit_of_work)


def get_consultar_nota_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ConsultarNotaService:
    return ConsultarNotaService(unit_of_work=unit_of_work)


def get_listar_notas_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ListarNotasService:
    return ListarNotasService(unit_of_work=unit_of_work)


def get_listar_submissoes_da_nota_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ListarSubmissoesDaNotaService:
    return ListarSubmissoesDaNotaService(unit_of_work=unit_of_work)


def get_consultar_pessoa_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ConsultarPessoaService:
    return ConsultarPessoaService(unit_of_work=unit_of_work)


def get_listar_notas_da_pessoa_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ListarNotasDaPessoaService:
    return ListarNotasDaPessoaService(unit_of_work=unit_of_work)


def get_iniciar_execucao_cadastro_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> IniciarExecucaoCadastroService:
    return IniciarExecucaoCadastroService(unit_of_work=unit_of_work)


def get_registrar_resultado_cadastro_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> RegistrarResultadoCadastroService:
    return RegistrarResultadoCadastroService(unit_of_work=unit_of_work)


def get_listar_execucoes_cadastro_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ListarExecucoesCadastroService:
    return ListarExecucoesCadastroService(unit_of_work=unit_of_work)


def get_reprocessar_nota_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ReprocessarNotaService:
    return ReprocessarNotaService(unit_of_work=unit_of_work)


def get_obter_proxima_nota_worker_service(
    unit_of_work: Annotated[Transaction, Depends(get_unit_of_work)],
) -> ObterProximaNotaParaProcessamentoService:
    return ObterProximaNotaParaProcessamentoService(unit_of_work=unit_of_work)


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
