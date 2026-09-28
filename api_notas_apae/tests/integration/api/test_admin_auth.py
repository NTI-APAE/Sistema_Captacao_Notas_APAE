from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_session
from app.infrastructure.admin_auth import password_hash
from app.infrastructure.config import get_settings
from app.main import create_app
from app.models.sessao_admin_model import SessaoAdminModel
from app.models.usuario_admin_model import UsuarioAdminModel


@pytest.fixture()
def auth_client(session_factory, monkeypatch):
    monkeypatch.setenv("ADMIN_SESSION_COOKIE", "test_admin_session")
    monkeypatch.setenv("ADMIN_SESSION_MINUTES", "60")
    monkeypatch.setenv("ADMIN_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    with session_factory() as session:
        session.add_all(
            [
                UsuarioAdminModel(
                    id=uuid4(),
                    nome="Maria",
                    email="maria@apae.org.br",
                    senha_hash=password_hash.hash("uma-senha-bem-segura"),
                    role="ADMIN",
                    ativo=True,
                ),
                UsuarioAdminModel(
                    id=uuid4(),
                    nome="Inativa",
                    email="inativa@apae.org.br",
                    senha_hash=password_hash.hash("uma-senha-bem-segura"),
                    role="ADMIN",
                    ativo=False,
                ),
            ]
        )
        session.commit()
    app = create_app()

    def session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        yield client, session_factory
    get_settings.cache_clear()


def test_login_cria_cookie_httponly_e_sessao_com_hash(auth_client):
    client, factory = auth_client
    response = client.post(
        "/admin/auth/login",
        json={"email": " MARIA@APAE.ORG.BR ", "senha": "uma-senha-bem-segura"},
    )
    assert response.status_code == 200
    assert response.json()["scopes"] == ["dashboard:read"]
    cookie = response.headers["set-cookie"]
    assert "test_admin_session=" in cookie
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Cache-Control" in response.headers
    token = client.cookies.get("test_admin_session")
    with factory() as session:
        stored = session.scalar(select(SessaoAdminModel))
        assert stored is not None
        assert token not in stored.token_hash
        assert len(stored.token_hash) == 64


@pytest.mark.parametrize(
    "email,senha",
    [
        ("maria@apae.org.br", "senha-incorreta"),
        ("ninguem@apae.org.br", "senha-incorreta"),
        ("inativa@apae.org.br", "uma-senha-bem-segura"),
    ],
)
def test_login_nao_revela_usuario(email, senha, auth_client):
    client, _ = auth_client
    response = client.post("/admin/auth/login", json={"email": email, "senha": senha})
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha inválidos"
    assert "test_admin_session" not in response.cookies


def test_me_reconhece_usuario_e_logout_revoga(auth_client):
    client, factory = auth_client
    assert client.get("/admin/auth/me").status_code == 401
    assert (
        client.post(
            "/admin/auth/login",
            json={"email": "maria@apae.org.br", "senha": "uma-senha-bem-segura"},
        ).status_code
        == 200
    )
    me = client.get("/admin/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "maria@apae.org.br"
    assert client.post("/admin/auth/logout").status_code == 204
    assert client.get("/admin/auth/me").status_code == 401
    with factory() as session:
        stored = session.scalar(select(SessaoAdminModel))
        assert stored.revogada_em is not None


def test_sessao_expirada_e_usuario_desativado_perdem_acesso(auth_client):
    client, factory = auth_client
    client.post(
        "/admin/auth/login",
        json={"email": "maria@apae.org.br", "senha": "uma-senha-bem-segura"},
    )
    with factory() as session:
        stored = session.scalar(select(SessaoAdminModel))
        stored.expira_em = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    assert client.get("/admin/auth/me").status_code == 401


def test_validacao_de_entrada_nao_aceita_senha_curta(auth_client):
    client, _ = auth_client
    response = client.post(
        "/admin/auth/login", json={"email": "maria@apae.org.br", "senha": "curta"}
    )
    assert response.status_code == 422


def test_cinco_falhas_bloqueiam_temporariamente(auth_client):
    client, factory = auth_client
    for _ in range(5):
        response = client.post(
            "/admin/auth/login",
            json={"email": "maria@apae.org.br", "senha": "senha-errada"},
        )
        assert response.status_code == 401
    # Mesmo a senha correta não libera o bloqueio antecipadamente.
    assert (
        client.post(
            "/admin/auth/login",
            json={"email": "maria@apae.org.br", "senha": "uma-senha-bem-segura"},
        ).status_code
        == 401
    )
    with factory() as session:
        usuario = session.scalar(
            select(UsuarioAdminModel).where(
                UsuarioAdminModel.email == "maria@apae.org.br"
            )
        )
        assert usuario.falhas_login >= 5
        assert usuario.bloqueado_ate is not None
