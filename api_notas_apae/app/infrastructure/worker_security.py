from typing import Annotated

from fastapi import Header, HTTPException, status

from app.infrastructure.config import get_settings


def validate_worker_api_key(
    api_key: Annotated[str | None, Header(alias="X-Worker-API-Key")] = None,
) -> None:
    expected_key = get_settings().worker_api_key
    if not expected_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker API key invalida.",
        )
