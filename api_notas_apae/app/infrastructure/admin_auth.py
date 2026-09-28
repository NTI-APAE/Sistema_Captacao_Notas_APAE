import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.infrastructure.config import get_settings
from app.models.sessao_admin_model import SessaoAdminModel
from app.models.usuario_admin_model import UsuarioAdminModel

password_hash = PasswordHash.recommended()
# Evita diferença de custo observável entre e-mail existente e inexistente.
_DUMMY_HASH = password_hash.hash("senha-inexistente-para-verificacao")
ROLE_SCOPES = {
    "ADMIN": frozenset({"dashboard:read"}),
    "LEITURA": frozenset({"dashboard:read"}),
}


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    id: UUID
    nome: str
    email: str
    role: str
    scopes: frozenset[str]


def normalizar_email(email: str) -> str:
    return email.strip().casefold()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def autenticar_usuario(session: Session, email: str, senha: str) -> UsuarioAdminModel:
    usuario = session.scalar(
        select(UsuarioAdminModel).where(
            UsuarioAdminModel.email == normalizar_email(email)
        )
    )
    now = datetime.now(UTC)
    valid = password_hash.verify(senha, usuario.senha_hash if usuario else _DUMMY_HASH)
    bloqueado_ate = usuario.bloqueado_ate if usuario else None
    if bloqueado_ate and bloqueado_ate.tzinfo is None:
        bloqueado_ate = bloqueado_ate.replace(tzinfo=UTC)
    bloqueado = bool(bloqueado_ate and bloqueado_ate > now)
    if usuario is not None and (not valid or bloqueado):
        usuario.falhas_login += 1
        if usuario.falhas_login >= 5:
            usuario.bloqueado_ate = now + timedelta(minutes=15)
        session.commit()
    if usuario is None or not valid or not usuario.ativo or bloqueado:
        raise HTTPException(401, "E-mail ou senha inválidos")
    if usuario.role not in ROLE_SCOPES:
        raise HTTPException(403, "Perfil administrativo sem permissão")
    usuario.falhas_login = 0
    usuario.bloqueado_ate = None
    return usuario


def criar_sessao(session: Session, usuario: UsuarioAdminModel) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    session.execute(delete(SessaoAdminModel).where(SessaoAdminModel.expira_em <= now))
    session.add(
        SessaoAdminModel(
            id=uuid4(),
            usuario_id=usuario.id,
            token_hash=hash_token(token),
            expira_em=now + timedelta(minutes=settings.admin_session_minutes),
            criado_em=now,
            ultimo_uso_em=now,
        )
    )
    usuario.ultimo_login = now
    session.commit()
    return token


def obter_principal(request: Request, session: Session) -> AdminPrincipal:
    token = request.cookies.get(get_settings().admin_session_cookie)
    if not token or len(token) > 200:
        raise HTTPException(401, "Autenticação necessária")
    now = datetime.now(UTC)
    row = session.execute(
        select(SessaoAdminModel, UsuarioAdminModel)
        .join(UsuarioAdminModel, SessaoAdminModel.usuario_id == UsuarioAdminModel.id)
        .where(
            SessaoAdminModel.token_hash == hash_token(token),
            SessaoAdminModel.revogada_em.is_(None),
            SessaoAdminModel.expira_em > now,
            UsuarioAdminModel.ativo.is_(True),
        )
    ).first()
    if row is None:
        raise HTTPException(401, "Sessão inválida ou expirada")
    sessao, usuario = row
    scopes = ROLE_SCOPES.get(usuario.role, frozenset())
    sessao.ultimo_uso_em = now
    session.commit()
    return AdminPrincipal(usuario.id, usuario.nome, usuario.email, usuario.role, scopes)


def require_admin_access(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> AdminPrincipal:
    principal = obter_principal(request, session)
    if "dashboard:read" not in principal.scopes:
        raise HTTPException(403, "Acesso administrativo não autorizado")
    return principal


def revogar_sessao(request: Request, session: Session) -> None:
    token = request.cookies.get(get_settings().admin_session_cookie)
    if not token:
        return
    sessao = session.scalar(
        select(SessaoAdminModel).where(
            SessaoAdminModel.token_hash == hash_token(token),
            SessaoAdminModel.revogada_em.is_(None),
        )
    )
    if sessao:
        sessao.revogada_em = datetime.now(UTC)
        session.commit()
