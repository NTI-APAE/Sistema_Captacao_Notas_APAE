import logging
import os
from typing import Any

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _form_fields(**fields: Any) -> dict[str, str]:
    return {
        name: str(value).lower() if isinstance(value, bool) else str(value)
        for name, value in fields.items()
        if value is not None
    }


async def processar_imagem(
    imagem: bytes,
    *,
    message_id: str,
    instance: str,
    remote_jid: str,
    from_me: bool = False,
    message_type: str | None = None,
    timestamp: str | int | None = None,
    push_name: str | None = None,
    mimetype: str | None = None,
    caption: str | None = None,
    remote_jid_alt: str | None = None,
) -> dict:
    url = os.getenv("NOTAS_API_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("NOTAS_API_INTERNAL_KEY")
    if not token:
        raise HTTPException(503, "Chave interna da API nao configurada")

    data = _form_fields(
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
    files = {
        "imagem": (
            "imagem",
            imagem,
            mimetype or "application/octet-stream",
        )
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{url}/notas/processar-imagem",
                headers={"X-Internal-API-Key": token},
                data=data,
                files=files,
            )
            if response.status_code in (409, 413, 415, 422):
                raise HTTPException(
                    response.status_code,
                    "Imagem ou evento rejeitado pela API",
                )
            response.raise_for_status()
            result = response.json()
            if (
                not isinstance(result, dict)
                or result.get("received") is not True
                or not isinstance(result.get("saved"), bool)
                or not isinstance(result.get("submissoes"), list)
            ):
                raise ValueError("Resposta incompleta")
            logger.info(
                "Envio para API de notas: OK",
                extra={
                    "event": "notes_api_forward",
                    "result": "ok",
                    "saved": result["saved"],
                    "replayed": result.get("replayed", False),
                },
            )
            return result
    except httpx.TimeoutException as error:
        logger.warning("Envio para API de notas: timeout")
        raise HTTPException(
            504,
            "Tempo limite da API de notas; reenvie o mesmo evento",
        ) from error
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("Envio para API de notas: falha de comunicacao")
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel confirmar o registro na API de notas",
        ) from error
