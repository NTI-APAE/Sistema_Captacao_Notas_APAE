import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.infrastructure.dependencies import (
    get_consultar_execucao_worker_service,
    get_obter_proxima_nota_worker_service,
    get_registrar_resultado_cadastro_service,
)
from app.infrastructure.worker_security import validate_worker_api_key
from app.schemas.execucao_cadastro_input import (
    RegistrarResultadoCadastroInput,
)
from app.schemas.execucao_schemas import (
    ExecucaoCadastroResponse,
)
from app.schemas.worker_schemas import (
    WorkerExecucaoResponse,
    WorkerNotaClaimResponse,
    WorkerResultadoRequest,
)
from app.services.execucoes import (
    RegistrarResultadoCadastroService,
)
from app.services.worker import (
    ConsultarExecucaoWorkerService,
    ObterProximaNotaParaProcessamentoService,
)

router = APIRouter(
    prefix="/worker",
    tags=["worker"],
    dependencies=[Depends(validate_worker_api_key)],
)


logger = logging.getLogger(__name__)


@router.post(
    "/notas/proxima",
    response_model=WorkerNotaClaimResponse,
    summary="Reservar proxima nota pendente",
    description=(
        "Reserva atomicamente a proxima nota pendente e cria uma execucao "
        "de cadastro para o automatizador."
    ),
    responses={
        200: {"description": "Nota reservada para processamento."},
        204: {"description": "Nao ha notas pendentes para processamento."},
        401: {"description": "API key do Worker ausente ou invalida."},
        409: {"description": "Conflito de estado."},
    },
)
def obter_proxima_nota(
    service: Annotated[
        ObterProximaNotaParaProcessamentoService,
        Depends(get_obter_proxima_nota_worker_service),
    ],
) -> WorkerNotaClaimResponse | Response:
    output = service.execute()
    if output is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return WorkerNotaClaimResponse.from_output(output)


@router.get(
    "/execucoes/{execucao_id}",
    response_model=WorkerExecucaoResponse,
    summary="Consultar execucao do Worker",
    responses={
        200: {"description": "Execucao encontrada."},
        401: {"description": "API key do Worker ausente ou invalida."},
        404: {"description": "Execucao nao encontrada."},
    },
)
def consultar_execucao(
    execucao_id: UUID,
    service: Annotated[
        ConsultarExecucaoWorkerService,
        Depends(get_consultar_execucao_worker_service),
    ],
) -> WorkerExecucaoResponse:
    return WorkerExecucaoResponse.from_output(service.execute(execucao_id))


@router.post(
    "/execucoes/{execucao_id}/resultado",
    response_model=ExecucaoCadastroResponse,
    summary="Registrar resultado do Worker",
    description="Registra o resultado da execucao realizada pelo automatizador.",
    responses={
        200: {"description": "Resultado registrado ou repetido idempotentemente."},
        401: {"description": "API key do Worker ausente ou invalida."},
        404: {"description": "Execucao nao encontrada."},
        409: {"description": "Resultado conflitante ou transicao invalida."},
        422: {"description": "Payload invalido."},
    },
)
def registrar_resultado_worker(
    execucao_id: UUID,
    request: WorkerResultadoRequest,
    service: Annotated[
        RegistrarResultadoCadastroService,
        Depends(get_registrar_resultado_cadastro_service),
    ],
) -> ExecucaoCadastroResponse:
    output = service.execute(
        RegistrarResultadoCadastroInput(
            execucao_id=execucao_id,
            status=request.status,
            mensagem=request.mensagem,
            valor=request.valor,
            data_emissao=request.data_emissao,
            tempo_segundos=request.tempo_segundos,
        ),
    )
    logger.info(
        "worker retornou resultado",
        extra={
            "event": "worker_result",
            "execucao_id": str(execucao_id),
            "nota_id": str(output.nota_fiscal_id),
            "resultado": output.status.value,
        },
    )
    return ExecucaoCadastroResponse.from_output(output)
