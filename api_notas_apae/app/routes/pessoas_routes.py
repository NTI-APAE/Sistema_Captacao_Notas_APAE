from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.infrastructure.dependencies import (
    get_consultar_pessoa_service,
    get_listar_notas_da_pessoa_service,
)
from app.schemas.nota_schemas import NotaFiscalResponse
from app.schemas.pessoa_schemas import PessoaResponse
from app.services.notas import ListarNotasDaPessoaService
from app.services.pessoas import ConsultarPessoaService

router = APIRouter(prefix="/pessoas", tags=["pessoas"])


@router.get(
    "/telefone/{telefone}",
    response_model=PessoaResponse,
    summary="Consultar pessoa por telefone",
)
def consultar_pessoa_por_telefone(
    telefone: str,
    service: Annotated[ConsultarPessoaService, Depends(get_consultar_pessoa_service)],
) -> PessoaResponse:
    return PessoaResponse.from_output(service.por_telefone(telefone))


@router.get(
    "/{pessoa_id}",
    response_model=PessoaResponse,
    summary="Consultar pessoa por ID",
)
def consultar_pessoa(
    pessoa_id: UUID,
    service: Annotated[ConsultarPessoaService, Depends(get_consultar_pessoa_service)],
) -> PessoaResponse:
    return PessoaResponse.from_output(service.por_id(pessoa_id))


@router.get(
    "/{pessoa_id}/notas",
    response_model=list[NotaFiscalResponse],
    summary="Listar notas unicas de uma pessoa",
    description=(
        "Retorna NotaFiscal sem duplicar o resultado quando a mesma pessoa "
        "submeteu a mesma nota mais de uma vez."
    ),
)
def listar_notas_da_pessoa(
    pessoa_id: UUID,
    service: Annotated[
        ListarNotasDaPessoaService,
        Depends(get_listar_notas_da_pessoa_service),
    ],
) -> list[NotaFiscalResponse]:
    return [NotaFiscalResponse.from_output(nota) for nota in service.execute(pessoa_id)]
