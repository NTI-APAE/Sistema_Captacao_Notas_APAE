import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.infrastructure.config import get_settings
from app.infrastructure.dependencies import get_unit_of_work
from app.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.imagem import ProcessarImagemResponse
from app.services.processar_imagem import (
    EventoConflitante,
    ProcessamentoConcorrente,
    ProcessarImagemMetadata,
    ProcessarImagemService,
)
from app.services.qr_code import MAX_IMAGE_BYTES


def autenticar_integracao(request: Request):
    expected = (
        os.getenv("NOTAS_API_INTERNAL_KEY")
        or get_settings().notas_api_internal_key
    )
    if not expected:
        raise HTTPException(503, "Chave interna da API nao configurada")
    supplied = request.headers.get("x-internal-api-key", "")
    if not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, "Credencial interna invalida")


router = APIRouter(
    prefix="/notas",
    tags=["processamento de imagem"],
    dependencies=[Depends(autenticar_integracao)],
)


@router.post("/processar-imagem", response_model=ProcessarImagemResponse)
async def processar_imagem(
    imagem: Annotated[UploadFile, File(description="Imagem recebida")],
    uow: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
    message_id: Annotated[str, Form(min_length=1, max_length=255)],
    instance: Annotated[str, Form(min_length=1, max_length=100)],
    remote_jid: Annotated[str, Form(min_length=1, max_length=255)],
    from_me: Annotated[bool, Form()] = False,
    message_type: Annotated[str | None, Form(max_length=100)] = None,
    timestamp: Annotated[str | None, Form(max_length=64)] = None,
    push_name: Annotated[str | None, Form(max_length=255)] = None,
    mimetype: Annotated[str | None, Form(max_length=100)] = None,
    caption: Annotated[str | None, Form(max_length=4096)] = None,
    remote_jid_alt: Annotated[str | None, Form(max_length=255)] = None,
) -> ProcessarImagemResponse:
    """Recebe imagem multipart e metadados da mensagem da Evolution."""
    body = bytearray()
    try:
        while chunk := await imagem.read(1024 * 1024):
            if len(body) + len(chunk) > MAX_IMAGE_BYTES:
                raise HTTPException(413, "Imagem acima do limite de 10 MB")
            body.extend(chunk)
    finally:
        await imagem.close()

    if from_me:
        return ProcessarImagemResponse(
            saved=False,
            reason="Mensagem enviada pelo proprio bot ignorada",
        )

    metadata = ProcessarImagemMetadata(
        message_id=message_id,
        instance=instance,
        remote_jid=remote_jid,
        remote_jid_alt=remote_jid_alt,
        from_me=from_me,
        message_type=message_type,
        timestamp=timestamp,
        push_name=push_name,
        mimetype=mimetype,
        caption=caption,
    )
    try:
        return await run_in_threadpool(
            ProcessarImagemService(uow).execute,
            bytes(body),
            metadata,
        )
    except EventoConflitante as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, "Imagem ou metadados invalidos") from error
    except (ProcessamentoConcorrente, SQLAlchemyError) as error:
        raise HTTPException(
            503,
            "Processamento indisponivel; reenvie o mesmo evento",
            headers={"Retry-After": "5"},
        ) from error
