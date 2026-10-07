from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError

from app.domain.enums.nota_status import NotaStatus
from app.domain.enums.submissao_status import SubmissaoStatus
from app.infrastructure.admin_auth import require_admin_access
from app.infrastructure.admin_reporting_dependencies import (
    get_admin_reporting_service,
    get_filtro,
)
from app.schemas.admin_reporting import (
    ContatoLista,
    HistoricoContato,
    NotaDetalhe,
    NotaLista,
    Pagina,
    ResumoAdmin,
    ResumoLeitorAdmin,
)
from app.schemas.admin_reporting_filters import AdminReportingFilter
from app.services.admin_reporting_service import AdminReportingService


class AdminReportingRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request):
            try:
                response = await handler(request)
            except HTTPException as error:
                codes = {
                    401: "authentication_required",
                    403: "forbidden",
                    404: "not_found",
                    422: "invalid_filters",
                    503: "authentication_unavailable",
                }
                response = JSONResponse(
                    {
                        "code": codes.get(error.status_code, "request_failed"),
                        "detail": error.detail,
                    },
                    status_code=error.status_code,
                )
            except RequestValidationError:
                response = JSONResponse(
                    {"code": "invalid_filters", "detail": "Parâmetros inválidos."},
                    status_code=422,
                )
            except SQLAlchemyError:
                response = JSONResponse(
                    {
                        "code": "database_unavailable",
                        "detail": "Não foi possível consultar os dados.",
                    },
                    status_code=503,
                )
            response.headers.update(
                {
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                }
            )
            return response

        return safe_handler


router = APIRouter(
    prefix="/admin/relatorios",
    tags=["relatórios administrativos"],
    dependencies=[Depends(require_admin_access)],
    route_class=AdminReportingRoute,
)
Service = Annotated[AdminReportingService, Depends(get_admin_reporting_service)]
Filtro = Annotated[AdminReportingFilter, Depends(get_filtro)]


@router.get("/resumo", response_model=ResumoAdmin)
def resumo(service: Service):
    return service.resumo()


@router.get("/opcoes")
def opcoes():
    return {"status": list(SubmissaoStatus), "cadastros": list(NotaStatus)}


@router.get("/leitor", response_model=ResumoLeitorAdmin)
def leitor(service: Service, filtro: Filtro):
    return service.leitor(filtro)


@router.get("/notas", response_model=Pagina[NotaLista])
def notas(service: Service, filtro: Filtro):
    return service.notas(filtro)


@router.get("/notas/{submissao_id}", response_model=NotaDetalhe)
def nota(submissao_id: UUID, service: Service):
    item = service.nota(submissao_id)
    if item is None:
        raise HTTPException(404, "Nota recebida não encontrada")
    return item


@router.get("/contatos", response_model=Pagina[ContatoLista])
def contatos(service: Service, filtro: Filtro):
    return service.contatos(filtro)


@router.get("/contatos/{pessoa_id}", response_model=HistoricoContato)
def contato(pessoa_id: UUID, service: Service, filtro: Filtro):
    item = service.contato(pessoa_id, filtro)
    if item is None:
        raise HTTPException(404, "Contato não encontrado")
    return item
