from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_session
from app.infrastructure.admin_auth import (
    ROLE_SCOPES,
    AdminPrincipal,
    autenticar_usuario,
    criar_sessao,
    require_admin_access,
    revogar_sessao,
)
from app.infrastructure.config import get_settings
from app.schemas.admin_auth import LoginAdminRequest, UsuarioAdminResponse

router = APIRouter(prefix="/admin/auth", tags=["autenticação administrativa"])


def response_usuario(principal: AdminPrincipal) -> UsuarioAdminResponse:
    return UsuarioAdminResponse(
        nome=principal.nome,
        email=principal.email,
        role=principal.role,
        scopes=sorted(principal.scopes),
    )


@router.post("/login", response_model=UsuarioAdminResponse)
def login(
    data: LoginAdminRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> UsuarioAdminResponse:
    usuario = autenticar_usuario(session, data.email, data.senha)
    token = criar_sessao(session, usuario)
    settings = get_settings()
    response.set_cookie(
        key=settings.admin_session_cookie,
        value=token,
        max_age=settings.admin_session_minutes * 60,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return UsuarioAdminResponse(
        nome=usuario.nome,
        email=usuario.email,
        role=usuario.role,
        scopes=sorted(ROLE_SCOPES[usuario.role]),
    )


@router.get("/me", response_model=UsuarioAdminResponse)
def me(
    principal: Annotated[AdminPrincipal, Depends(require_admin_access)],
) -> UsuarioAdminResponse:
    return response_usuario(principal)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    revogar_sessao(request, session)
    settings = get_settings()
    response.delete_cookie(
        settings.admin_session_cookie,
        path="/",
        secure=settings.admin_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
