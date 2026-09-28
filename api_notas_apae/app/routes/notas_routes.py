from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.domain.enums.nota_status import NotaStatus
from app.infrastructure.dependencies import (
    get_consultar_nota_service,
    get_iniciar_execucao_cadastro_service,
    get_listar_execucoes_cadastro_service,
    get_listar_notas_service,
    get_listar_submissoes_da_nota_service,
    get_registrar_resultado_cadastro_service,
    get_reprocessar_nota_service,
)
from app.schemas.execucao_cadastro_input import (
    RegistrarResultadoCadastroInput,
)
from app.schemas.execucao_schemas import (
    ExecucaoCadastroResponse,
    RegistrarResultadoCadastroRequest,
)
from app.schemas.nota_schemas import (
    NotaFiscalResponse,
    PaginatedNotasResponse,
)
from app.schemas.pagination import ListarNotasFiltro
from app.schemas.submissao_history_schemas import (
    SubmissaoNotaResponse,
)
from app.services.execucoes import (
    IniciarExecucaoCadastroService,
    ListarExecucoesCadastroService,
    RegistrarResultadoCadastroService,
)
from app.services.notas import (
    ConsultarNotaService,
    ListarNotasService,
    ListarSubmissoesDaNotaService,
    ReprocessarNotaService,
)

router = APIRouter(prefix="/notas", tags=["notas"])


@router.get(
    "",
    response_model=PaginatedNotasResponse,
    summary="Listar notas fiscais",
    description="Lista NotaFiscal com paginacao e filtros opcionais.",
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
    "/chave/{chave}",
    response_model=NotaFiscalResponse,
    summary="Consultar nota por chave",
)
def consultar_nota_por_chave(
    chave: str,
    service: Annotated[ConsultarNotaService, Depends(get_consultar_nota_service)],
) -> NotaFiscalResponse:
    return NotaFiscalResponse.from_output(service.por_chave(chave))


@router.get(
    "/{nota_id}",
    response_model=NotaFiscalResponse,
    summary="Consultar nota por ID",
)
def consultar_nota(
    nota_id: UUID,
    service: Annotated[ConsultarNotaService, Depends(get_consultar_nota_service)],
) -> NotaFiscalResponse:
    return NotaFiscalResponse.from_output(service.por_id(nota_id))


@router.get(
    "/{nota_id}/submissoes",
    response_model=list[SubmissaoNotaResponse],
    summary="Listar submissoes da nota",
    description="Mostra o historico de SubmissaoNota associado a uma NotaFiscal.",
)
def listar_submissoes_da_nota(
    nota_id: UUID,
    service: Annotated[
        ListarSubmissoesDaNotaService,
        Depends(get_listar_submissoes_da_nota_service),
    ],
) -> list[SubmissaoNotaResponse]:
    return [
        SubmissaoNotaResponse.from_output(submissao)
        for submissao in service.execute(nota_id)
    ]


@router.post(
    "/{nota_id}/execucoes",
    response_model=ExecucaoCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar execucao de cadastro",
)
def iniciar_execucao(
    nota_id: UUID,
    service: Annotated[
        IniciarExecucaoCadastroService,
        Depends(get_iniciar_execucao_cadastro_service),
    ],
) -> ExecucaoCadastroResponse:
    return ExecucaoCadastroResponse.from_output(service.execute(nota_id))


@router.get(
    "/{nota_id}/execucoes",
    response_model=list[ExecucaoCadastroResponse],
    summary="Listar execucoes de cadastro",
)
def listar_execucoes(
    nota_id: UUID,
    service: Annotated[
        ListarExecucoesCadastroService,
        Depends(get_listar_execucoes_cadastro_service),
    ],
) -> list[ExecucaoCadastroResponse]:
    return [
        ExecucaoCadastroResponse.from_output(execucao)
        for execucao in service.execute(nota_id)
    ]


@router.post(
    "/{nota_id}/resultado-cadastro",
    response_model=ExecucaoCadastroResponse,
    summary="Registrar resultado de cadastro",
)
def registrar_resultado_cadastro(
    nota_id: UUID,
    request: RegistrarResultadoCadastroRequest,
    service: Annotated[
        RegistrarResultadoCadastroService,
        Depends(get_registrar_resultado_cadastro_service),
    ],
) -> ExecucaoCadastroResponse:
    return ExecucaoCadastroResponse.from_output(
        service.execute(
            RegistrarResultadoCadastroInput(
                nota_id=nota_id,
                execucao_id=request.execucao_id,
                status=request.status,
                mensagem=request.mensagem,
                valor=request.valor,
                data_emissao=request.data_emissao,
                tempo_segundos=request.tempo_segundos,
            ),
        ),
    )


@router.post(
    "/{nota_id}/reprocessar",
    response_model=NotaFiscalResponse,
    summary="Reprocessar nota fiscal",
    description="Retorna a NotaFiscal para PENDENTE quando seu estado for elegivel.",
)
def reprocessar_nota(
    nota_id: UUID,
    service: Annotated[
        ReprocessarNotaService,
        Depends(get_reprocessar_nota_service),
    ],
) -> NotaFiscalResponse:
    return NotaFiscalResponse.from_output(service.execute(nota_id))
