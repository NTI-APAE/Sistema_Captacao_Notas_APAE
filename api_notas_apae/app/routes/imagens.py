import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.domain.enums.origem_submissao import OrigemSubmissao
from app.infrastructure.config import get_settings
from app.infrastructure.dependencies import get_unit_of_work
from app.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.imagem import ProcessarImagemResponse
from app.services.processar_imagem import (
    EventoConflitante,
    ProcessamentoConcorrente,
    ProcessarImagemService,
)
from app.services.qr_code import MAX_IMAGE_BYTES


def autenticar_integracao(request: Request):
    # Fallback permite reutilizar a configuração atual sem editar .env real.
    expected = (
        os.getenv("NOTAS_INTERNAL_API_KEY")
        or os.getenv("WEBHOOK_TOKEN")
        or get_settings().notas_internal_api_key
        or get_settings().webhook_token
    )
    if not expected:
        raise HTTPException(503, "Chave interna da API não configurada")
    supplied = request.headers.get("x-internal-api-key", "")
    if not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, "Credencial interna inválida")


router = APIRouter(
    prefix="/notas",
    tags=["processamento de imagem"],
    dependencies=[Depends(autenticar_integracao)],
)


@router.post("/processar-imagem", response_model=ProcessarImagemResponse)
async def processar_imagem(
    request: Request,
    uow: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
    telefone: Annotated[str, Header(alias="X-Telefone", pattern=r"^[0-9]{8,15}$")],
    instancia: Annotated[
        str, Header(alias="X-Instancia", min_length=1, max_length=100)
    ],
    evento_id: Annotated[
        str, Header(alias="X-Evento-ID", min_length=1, max_length=255)
    ],
    origem: Annotated[OrigemSubmissao, Header(alias="X-Origem")],
):
    """Corpo binário (application/octet-stream), limite de 10 MiB.

    Identidade idempotente: origem + instancia + evento_id. O cliente deve
    reenviar os mesmos bytes e metadados após falha de comunicação.
    """
    if (
        request.headers.get("content-type", "").split(";")[0]
        != "application/octet-stream"
    ):
        raise HTTPException(415, "Envie application/octet-stream")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Imagem acima do limite de 10 MB")
        body.extend(chunk)
    try:
        return await run_in_threadpool(
            ProcessarImagemService(uow).execute,
            bytes(body),
            telefone,
            origem,
            instancia,
            evento_id,
        )
    except EventoConflitante as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, "Imagem inválida ou não decodificável") from error
    except (ProcessamentoConcorrente, SQLAlchemyError) as error:
        raise HTTPException(
            503,
            "Processamento indisponível; reenvie o mesmo evento",
            headers={"Retry-After": "5"},
        ) from error
