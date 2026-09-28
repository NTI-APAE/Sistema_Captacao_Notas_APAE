import os

import httpx
from fastapi import HTTPException


async def processar_imagem(
    imagem: bytes,
    telefone: str,
    instancia: str,
    evento_id: str,
) -> dict:
    url = os.getenv("NOTAS_API_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("NOTAS_INTERNAL_API_KEY") or os.getenv("WEBHOOK_TOKEN")
    if not token:
        raise HTTPException(503, "Chave interna da API não configurada")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{url}/notas/processar-imagem",
                content=imagem,
                headers={
                    "Content-Type": "application/octet-stream",
                    "X-Internal-API-Key": token,
                    "X-Telefone": telefone,
                    "X-Origem": "WHATSAPP",
                    "X-Instancia": instancia,
                    "X-Evento-ID": evento_id,
                },
            )
            # Erros definitivos não devem virar confirmação de salvamento.
            if response.status_code in (409, 413, 415, 422):
                raise HTTPException(
                    response.status_code, "Imagem ou evento rejeitado pela API"
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
            return result
    except httpx.TimeoutException as error:
        raise HTTPException(
            504,
            "Tempo limite da API de notas; reenvie o mesmo evento",
        ) from error
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível confirmar o registro na API de notas",
        ) from error
