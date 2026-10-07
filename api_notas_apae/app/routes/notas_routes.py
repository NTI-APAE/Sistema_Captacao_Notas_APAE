from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.domain.enums.nota_status import NotaStatus
from app.infrastructure.dependencies import (
    get_consultar_nota_service,
    get_listar_notas_service,
)
from app.infrastructure.worker_security import validate_worker_api_key
from app.schemas.nota_schemas import NotaFiscalResponse, PaginatedNotasResponse
from app.schemas.pagination import ListarNotasFiltro
from app.services.notas import ConsultarNotaService, ListarNotasService

router = APIRouter(prefix="/notas", tags=["notas"])


@router.get(
    "",
    response_model=PaginatedNotasResponse,
    summary="Listar notas fiscais",
    description="Lista NotaFiscal com paginacao e filtros opcionais.",
    dependencies=[Depends(validate_worker_api_key)],
)
def listar_notas(
    service: Annotated[ListarNotasService, Depends(get_listar_notas_service)],
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status: NotaStatus | None = None,
    data_inicial: date | None = None,
    data_final: date | None = None,
    telefone: str | None = None,
    chave: str | None = None,
) -> PaginatedNotasResponse:
    output = service.execute(
        ListarNotasFiltro(
            page=page,
            size=size,
            status=status,
            data_inicial=data_inicial,
            data_final=data_final,
            telefone=telefone,
            chave=chave,
        ),
    )
    return PaginatedNotasResponse(
        items=[NotaFiscalResponse.from_output(nota) for nota in output.items],
        page=output.page,
        size=output.size,
        total=output.total,
    )


@router.get(
    "/{nota_id}",
    response_model=NotaFiscalResponse,
    summary="Consultar nota por ID",
    dependencies=[Depends(validate_worker_api_key)],
)
def consultar_nota(
    nota_id: UUID,
    service: Annotated[ConsultarNotaService, Depends(get_consultar_nota_service)],
) -> NotaFiscalResponse:
    return NotaFiscalResponse.from_output(service.por_id(nota_id))
