import base64
import binascii
import os

import httpx
from fastapi import HTTPException

MAX_IMAGE_BYTES = 10 * 1024 * 1024

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080").rstrip("/")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "teste2")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")


async def recuperar_imagem(id_mensagem: str) -> tuple[bytes, str]:
    if not EVOLUTION_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="EVOLUTION_API_KEY não configurada",
        )

    url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE}"

    corpo = {
        "message": {
            "key": {
                "id": id_mensagem,
            }
        },
        "convertToMp4": False,
    }

    print("\n=== RECUPERAÇÃO DA IMAGEM ===", flush=True)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resposta = await client.post(
                url,
                headers={"apikey": EVOLUTION_API_KEY},
                json=corpo,
            )

            resposta.raise_for_status()
            resultado = resposta.json()

    except httpx.HTTPStatusError as erro:
        print(
            "Evolution retornou HTTP:",
            erro.response.status_code,
            flush=True,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Evolution retornou HTTP {erro.response.status_code}",
        ) from erro

    except httpx.RequestError as erro:
        print(
            "Falha de comunicação:",
            type(erro).__name__,
            flush=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Falha de comunicação com a Evolution",
        ) from erro

    except ValueError as erro:
        raise HTTPException(
            status_code=502,
            detail="Evolution retornou JSON inválido",
        ) from erro

    if not isinstance(resultado, dict):
        raise HTTPException(
            status_code=502,
            detail="Resposta inesperada da Evolution",
        )

    conteudo_base64 = resultado.get("base64")

    if not isinstance(conteudo_base64, str) or not conteudo_base64:
        raise HTTPException(
            status_code=502,
            detail="Evolution não retornou Base64",
        )

    if conteudo_base64.startswith("data:"):
        conteudo_base64 = conteudo_base64.split(",", 1)[-1]

    if len(conteudo_base64) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
        raise HTTPException(413, "Imagem acima do limite de 10 MB")

    try:
        imagem_bytes = base64.b64decode(
            conteudo_base64,
            validate=True,
        )
    except (ValueError, binascii.Error) as erro:
        raise HTTPException(
            status_code=502,
            detail="Base64 inválido",
        ) from erro

    if not imagem_bytes:
        raise HTTPException(
            status_code=502,
            detail="Imagem vazia",
        )

    if len(imagem_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Imagem acima do limite de 10 MB",
        )

    mimetype = resultado.get("mimetype") or "desconhecido"

    print("Imagem recuperada!", flush=True)
    print("MIME:", mimetype, flush=True)
    print("Tamanho:", len(imagem_bytes), "bytes", flush=True)

    return imagem_bytes, mimetype
