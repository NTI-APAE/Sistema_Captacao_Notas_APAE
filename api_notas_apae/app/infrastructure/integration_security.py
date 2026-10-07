import secrets

from fastapi import HTTPException, Request

from app.infrastructure.config import get_settings


def autenticar_integracao(request: Request) -> None:
    expected = get_settings().notas_api_internal_key
    if not expected:
        raise HTTPException(503, "Chave interna da API não configurada")
    supplied = request.headers.get("x-internal-api-key", "")
    if not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, "Credencial interna inválida")
