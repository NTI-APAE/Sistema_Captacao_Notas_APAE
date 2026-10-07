from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_session
from app.infrastructure.admin_auth import password_hash
from app.infrastructure.admin_reporting_dependencies import get_admin_reporting_service
from app.main import create_app
from app.models.consentimento_model import ConsentimentoModel as C
from app.models.evento_imagem import EventoImagem as E
from app.models.nota_fiscal_model import NotaFiscalModel as N
from app.models.pessoa_model import PessoaModel as P
from app.models.submissao_nota_model import SubmissaoNotaModel as S
from app.models.usuario_admin_model import UsuarioAdminModel as U


@pytest.fixture()
def admin_data(session_factory):
    ids = {name: uuid4() for name in ("ana", "nota", "dup")}
    now = datetime(2026, 9, 28, 3, tzinfo=UTC)
    with session_factory() as session:
        session.add_all(
            [
                U(
                    id=uuid4(),
                    nome="Operador",
                    email="operador@apae.org.br",
                    senha_hash=password_hash.hash("senha-segura-teste"),
                    role="ADMIN",
                    ativo=True,
                ),
                P(
                    id=ids["ana"],
                    telefone="559899991234",
                    nome="Ana",
                    ativo=True,
                    criado_em=now,
                    atualizado_em=now,
                ),
                N(
                    id=ids["nota"],
                    chave="2" * 44,
                    status="CADASTRADA",
                    valor=Decimal("100.00"),
                    data_emissao=date(2026, 9, 28),
                    criado_em=now,
                    atualizado_em=now,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                S(
                    id=ids["dup"],
                    pessoa_id=ids["ana"],
                    nota_fiscal_id=ids["nota"],
                    chave_extraida="2" * 44,
                    status="DUPLICADA",
                    origem="WHATSAPP",
                    data_recebimento=now,
                    evento_instancia="teste2",
                    evento_id="msg-admin",
                ),
                E(
                    origem="WHATSAPP",
                    instancia="teste2",
                    evento_id="msg-admin",
                    fingerprint="f" * 64,
                    resultado={"saved": True},
                    remote_jid="559899991234@s.whatsapp.net",
                    from_me=False,
                    message_type="imageMessage",
                    data_mensagem=datetime(2026, 9, 28, 2, 59, tzinfo=UTC),
                    criado_em=now,
                    push_name="Ana",
                    mimetype="image/png",
                    caption="nota da Ana",
                ),
                C(
                    id=uuid4(),
                    pessoa_id=ids["ana"],
                    tipo="LIGACAO",
                    aceito=False,
                    origem="WHATSAPP",
                    data_resposta=now,
                ),
            ]
        )
        session.commit()
    return ids


@pytest.fixture()
def admin_client(session_factory, admin_data):
    app = create_app()

    def session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        response = client.post(
            "/admin/auth/login",
            json={"email": "operador@apae.org.br", "senha": "senha-segura-teste"},
        )
        assert response.status_code == 200
        yield client


def test_resumo_json_e_privacidade(admin_client):
    response = admin_client.get("/admin/relatorios/resumo")
    assert response.status_code == 200
    result = response.json()
    assert result["indicadores"]["total"] == 1
    assert result["indicadores"]["notas"] == 1
    assert result["indicadores"]["notas_leitor"] == 0
    assert result["indicadores"]["notas_whatsapp"] == 1
    assert result["indicadores"]["total_geral"] == 1
    assert float(result["indicadores"]["valor_cadastradas"]) == 100
    assert float(result["indicadores"]["retorno_estimado"]) == 1
    assert result["indicadores"]["notas_erros"] == 0
    assert result["indicadores"]["notas_ignoradas"] == 0
    assert result["indicadores"]["reenvios_mensagens"] == 0
    assert len(result["series"]) == 30
    assert dict(result["status_submissoes"])["DUPLICADA"] == 1
    assert "559899991234" not in response.text
    assert "2" * 44 not in response.text
    assert "private-fingerprint" not in response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert result["result"]["items"][0]["data_recebimento"].endswith("Z")


def test_lista_json_filtrada_e_paginada(admin_client):
    response = admin_client.get("/admin/relatorios/notas?q=Ana&size=1")
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["page"] == 1
    assert len(result["items"]) == 1
    row = result["items"][0]
    assert row["telefone"] == "•••• 1234"
    assert row["chave"] == "2222…22222"
    assert "mensagem_whatsapp_id" not in row
    assert "erro_mensagem" not in row
    assert "imagem_path" not in row


def test_lista_inclui_nota_importada_pelo_leitor(admin_client, session_factory):
    nota_id = uuid4()
    chave = "3" * 44
    now = datetime(2026, 9, 29, 3, tzinfo=UTC)
    with session_factory() as session:
        session.add(
            N(
                id=nota_id,
                chave=chave,
                status="PENDENTE",
                criado_em=now,
                atualizado_em=now,
            )
        )
        session.commit()

    response = admin_client.get("/admin/relatorios/notas?chave=3333")
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["items"][0]["origem"] == "LEITOR_NOTA_FISCAL"
    assert result["items"][0]["status"] == "IMPORTADO"
    assert result["items"][0]["cadastro"] == "PENDENTE"

    summary = admin_client.get("/admin/relatorios/resumo")
    assert summary.status_code == 200
    assert summary.json()["indicadores"]["notas_leitor"] == 1

    detail = admin_client.get(f"/admin/relatorios/notas/{nota_id}")
    assert detail.status_code == 200
    assert detail.json()["origem"] == "LEITOR_NOTA_FISCAL"
    assert detail.json()["nota_fiscal_id"] == str(nota_id)


def test_contatos_json_e_ultimo_consentimento(admin_client):
    response = admin_client.get("/admin/relatorios/contatos?ligacao=false")
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["items"][0]["ligacao"] is False
    assert result["items"][0]["telefone"] == "•••• 1234"
    assert "559899991234" not in response.text


def test_detalhes_json_explicitos(admin_client, admin_data):
    note = admin_client.get(f"/admin/relatorios/notas/{admin_data['dup']}")
    assert note.status_code == 200
    assert note.json()["chave"] == "2" * 44
    assert note.json()["whatsapp_instance"] == "teste2"
    assert note.json()["whatsapp_message_id"] == "msg-admin"
    assert note.json()["whatsapp_caption"] == "nota da Ana"
    assert note.json()["atraso_processamento_segundos"] == 60
    assert note.json()["historico_mensagens"][0]["message_id"] == "msg-admin"
    assert "mensagem_status" not in note.json()
    assert "secret-internal" not in note.text
    contact = admin_client.get(f"/admin/relatorios/contatos/{admin_data['ana']}?size=1")
    assert contact.status_code == 200
    result = contact.json()
    assert result["contato"]["telefone"] == "559899991234"
    assert result["consentimentos"]["page"] == 1
    assert result["result"]["page"] == 1
    assert result["result"]["items"][0]["chave"] == "2222…22222"


def test_opcoes_vem_do_dominio(admin_client):
    response = admin_client.get("/admin/relatorios/opcoes")
    assert response.status_code == 200
    assert "DUPLICADA" in response.json()["status"]
    assert "CADASTRADA" in response.json()["cadastros"]


@pytest.mark.parametrize("path", ["resumo", "opcoes", "notas", "contatos"])
def test_api_fechada_por_padrao(path, session_factory):
    app = create_app()

    def session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        result = client.get(f"/admin/relatorios/{path}", headers={"x-user": "admin"})
    assert result.status_code == 401
    assert result.json()["code"] == "authentication_required"


@pytest.mark.parametrize("kind", ["notas", "contatos"])
def test_detalhe_json_inexistente(admin_client, kind):
    result = admin_client.get(f"/admin/relatorios/{kind}/{uuid4()}")
    assert result.status_code == 404
    assert result.json()["code"] == "not_found"


@pytest.mark.parametrize(
    "suffix",
    [
        "notas?size=0",
        "notas/invalid",
        "contatos?page=0",
        "notas?data_inicial=2026-10-01&data_final=2026-09-01",
    ],
)
def test_json_validacao_sem_eco_de_dados(admin_client, suffix):
    result = admin_client.get("/admin/relatorios/" + suffix)
    assert result.status_code == 422
    assert result.json()["code"] == "invalid_filters"
    assert "input" not in result.json()


def test_json_erro_banco_sem_vazamento(admin_client):
    def fail():
        raise SQLAlchemyError("password=secret telefone=559899991234")

    admin_client.app.dependency_overrides[get_admin_reporting_service] = fail
    result = admin_client.get("/admin/relatorios/resumo")
    assert result.status_code == 503
    assert result.json()["code"] == "database_unavailable"
    assert "secret" not in result.text


def test_json_somente_consulta(admin_client):
    assert admin_client.post("/admin/relatorios/notas").status_code == 405
