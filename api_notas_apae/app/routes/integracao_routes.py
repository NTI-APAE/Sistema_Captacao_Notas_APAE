from typing import Annotated

from fastapi import APIRouter, Depends

from app.infrastructure.dependencies import (
    get_registrar_resumo_operacao_leitor_service,
    get_unit_of_work,
)
from app.infrastructure.integration_security import autenticar_integracao
from app.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.importar_notas_input import (
    ImportarNotasTxtRequest,
    ImportarNotasTxtResponse,
)
from app.schemas.importar_notas_service_input import ImportarNotasInput
from app.schemas.resumo_operacao_leitor import (
    RegistrarResumoOperacaoLeitorRequest,
    ResumoOperacaoLeitorResponse,
)
from app.services.importar_notas import ImportarNotasTxtService
from app.services.resumos_leitor import RegistrarResumoOperacaoLeitorService

router = APIRouter(
    prefix="/integracao",
    tags=["integração"],
    dependencies=[Depends(autenticar_integracao)],
)


@router.post("/notas/importar-txt", response_model=ImportarNotasTxtResponse)
def importar_notas_txt(
    request: ImportarNotasTxtRequest,
    uow: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
) -> ImportarNotasTxtResponse:
    output = ImportarNotasTxtService(uow).execute(
        ImportarNotasInput(
            nome_arquivo=request.nome_arquivo,
            total_linhas=request.total_linhas,
            total_invalidas=request.total_invalidas,
            total_duplicadas_txt=request.total_duplicadas_txt,
            chaves=request.chaves,
        )
    )
    return ImportarNotasTxtResponse(
        total_linhas=output.total_linhas,
        total_validas=output.total_validas,
        total_invalidas=output.total_invalidas,
        total_duplicadas=output.total_duplicadas,
        total_inseridas=output.total_inseridas,
        total_reativadas=output.total_reativadas,
        total_ja_existentes=output.total_ja_existentes,
    )


@router.post(
    "/leitor/resumos",
    response_model=ResumoOperacaoLeitorResponse,
    summary="Registrar resumo da operacao do leitor",
    description=(
        "Persiste os totais e valores apurados pelo leitor ao concluir uma "
        "operacao. A mesma operacao pode ser reenviada idempotentemente."
    ),
)
def registrar_resumo_operacao_leitor(
    request: RegistrarResumoOperacaoLeitorRequest,
    service: Annotated[
        RegistrarResumoOperacaoLeitorService,
        Depends(get_registrar_resumo_operacao_leitor_service),
    ],
) -> ResumoOperacaoLeitorResponse:
    return ResumoOperacaoLeitorResponse.from_domain(service.execute(request))
