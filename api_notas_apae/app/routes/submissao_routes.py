from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.infrastructure.dependencies import get_registrar_submissao_service
from app.schemas.registrar_submissao_input import RegistrarSubmissaoInput
from app.schemas.submissao_schemas import (
    RegistrarSubmissaoRequest,
    RegistrarSubmissaoResponse,
)
from app.services.submissoes import RegistrarSubmissaoService

router = APIRouter(prefix="/submissoes", tags=["submissoes"])


@router.post(
    "",
    response_model=RegistrarSubmissaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar submissao manual",
    description=(
        "Cria uma SubmissaoNota manual. Se a NotaFiscal ja existir, "
        "cria uma nova submissao DUPLICADA apontando para a mesma nota."
    ),
)
def registrar_submissao(
    request: RegistrarSubmissaoRequest,
    response: Response,
    service: Annotated[
        RegistrarSubmissaoService,
        Depends(get_registrar_submissao_service),
    ],
) -> RegistrarSubmissaoResponse:
    output = service.execute(
        RegistrarSubmissaoInput(
            telefone=request.telefone,
            origem=request.origem,
            chave=request.chave,
        ),
    )
    response.status_code = status.HTTP_201_CREATED

    return RegistrarSubmissaoResponse(
        status=output.status,
        duplicada=output.duplicada,
        nota_id=output.nota_id,
        submissao_id=output.submissao_id,
    )
