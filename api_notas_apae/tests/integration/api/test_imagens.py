from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.models.evento_imagem import EventoImagem
from app.models.nota_fiscal_model import NotaFiscalModel
from app.models.submissao_nota_model import SubmissaoNotaModel
from app.services import processar_imagem


@pytest.fixture
def headers(monkeypatch):
    monkeypatch.setenv("NOTAS_API_INTERNAL_KEY", "test-internal")
    return {
        "X-Internal-API-Key": "test-internal",
        "message_id": "msg-1",
        "instance": "teste2",
        "remote_jid": "5598999999999@s.whatsapp.net",
        "from_me": "false",
        "message_type": "imageMessage",
        "timestamp": "1710000000",
        "push_name": "Ana",
        "mimetype": "image/png",
        "caption": "nota",
    }


def enviar(client, headers, imagem):
    auth_headers = {"X-Internal-API-Key": headers["X-Internal-API-Key"]}
    data = {
        key: value
        for key, value in headers.items()
        if not key.startswith("X-") and value not in (None, "")
    }
    return client.post(
        "/notas/processar-imagem",
        headers=auth_headers,
        data=data,
        files={"imagem": ("nota.png", imagem, data.get("mimetype"))},
    )


def test_imagem_real_replay_e_nova_mensagem(
    client, headers, imagem_qr, session_factory
):
    first = enviar(client, headers, imagem_qr)
    assert first.status_code == 200
    assert first.json()["saved"] is True
    with patch.object(
        processar_imagem,
        "ler_qr_code",
        side_effect=AssertionError("Replay nao deve reler QR"),
    ):
        replay = enviar(client, headers, imagem_qr)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["submissoes"] == first.json()["submissoes"]
    nova = enviar(client, {**headers, "message_id": "msg-2"}, imagem_qr)
    assert nova.status_code == 200
    assert nova.json()["submissoes"][0]["duplicada"] is True
    assert (
        nova.json()["submissoes"][0]["submissao_id"]
        != first.json()["submissoes"][0]["submissao_id"]
    )
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(NotaFiscalModel)) == 1
        assert session.scalar(select(func.count()).select_from(SubmissaoNotaModel)) == 2
        assert session.scalar(select(func.count()).select_from(EventoImagem)) == 2
        evento = session.get(EventoImagem, ("WHATSAPP", "teste2", "msg-1"))
        assert evento is not None
        assert evento.remote_jid == headers["remote_jid"]
        assert evento.message_type == "imageMessage"
        assert evento.push_name == "Ana"
        assert evento.mimetype == "image/png"
        assert evento.caption == "nota"
        assert evento.reenvios == 1
        submissao = session.get(
            SubmissaoNotaModel,
            UUID(first.json()["submissoes"][0]["submissao_id"]),
        )
        assert submissao is not None
        assert submissao.evento_instancia == "teste2"
        assert submissao.evento_id == "msg-1"


def test_conteudo_conflitante(client, headers, imagem_qr, imagem_sem_qr):
    assert enviar(client, headers, imagem_qr).status_code == 200
    assert enviar(client, headers, imagem_sem_qr).status_code == 409


def test_sem_qr_persiste_resultado(client, headers, imagem_sem_qr):
    result = enviar(client, headers, imagem_sem_qr)
    assert result.status_code == 200
    assert result.json()["saved"] is False
    assert enviar(client, headers, imagem_sem_qr).json()["replayed"] is True


def test_invalida_nao_reserva_evento(client, headers, imagem_qr):
    assert enviar(client, headers, b"invalid").status_code == 422
    assert enviar(client, headers, imagem_qr).json()["saved"] is True


def test_autenticacao_e_limite(client, headers, imagem_qr):
    assert (
        enviar(
            client,
            {**headers, "X-Internal-API-Key": "wrong"},
            imagem_qr,
        ).status_code
        == 401
    )
    assert (
        enviar(
            client,
            {**headers, "message_id": "mime-test", "mimetype": "text/plain"},
            imagem_qr,
        ).status_code
        == 200
    )
    assert (
        enviar(
            client,
            {**headers, "message_id": "too-large"},
            b"0" * (10 * 1024 * 1024 + 1),
        ).status_code
        == 413
    )


def test_campos_opcionais_ausentes(client, headers, imagem_sem_qr):
    required = {
        key: headers[key]
        for key in ("X-Internal-API-Key", "message_id", "instance", "remote_jid")
    }

    result = enviar(client, required, imagem_sem_qr)

    assert result.status_code == 200
    assert result.json()["saved"] is False


def test_from_me_e_ignorado(client, headers, imagem_qr, session_factory):
    result = enviar(
        client,
        {**headers, "from_me": "true"},
        imagem_qr,
    )

    assert result.status_code == 200
    assert result.json()["saved"] is False
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(EventoImagem)) == 0


@pytest.mark.parametrize("mesmo_evento", [True, False])
def test_concorrencia(client, headers, chave_valida, session_factory, mesmo_evento):
    barrier = Barrier(2)

    def ler(_):
        barrier.wait(timeout=10)
        return [chave_valida]

    def post(index):
        message_id = "same" if mesmo_evento else str(index)
        metadata = {**headers, "message_id": message_id}
        return enviar(client, metadata, b"image").json()

    with (
        patch.object(processar_imagem, "ler_qr_code", side_effect=ler),
        ThreadPoolExecutor(2) as pool,
    ):
        results = list(pool.map(post, range(2)))
    assert all(r.get("saved") for r in results), results
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(NotaFiscalModel)) == 1
        assert session.scalar(select(func.count()).select_from(SubmissaoNotaModel)) == (
            1 if mesmo_evento else 2
        )
    if mesmo_evento:
        assert sorted(r["replayed"] for r in results) == [False, True]
    else:
        assert sorted(r["submissoes"][0]["duplicada"] for r in results) == [
            False,
            True,
        ]


def test_lote_atomico_e_retry(client, headers, chave_valida, session_factory):
    original = processar_imagem.registrar_em_transacao
    count = 0

    def fail_second(uow, data):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("falha simulada")
        return original(uow, data)

    with (
        patch.object(processar_imagem, "ler_qr_code", return_value=["a", "b"]),
        patch.object(
            processar_imagem,
            "extrair_chave_acesso",
            side_effect=[chave_valida, "1" * 44],
        ),
        patch.object(
            processar_imagem, "registrar_em_transacao", side_effect=fail_second
        ),
    ):
        with pytest.raises(RuntimeError):
            enviar(client, headers, b"image")
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(SubmissaoNotaModel)) == 0
        assert session.scalar(select(func.count()).select_from(EventoImagem)) == 0
        assert session.scalar(select(func.count()).select_from(NotaFiscalModel)) == 0
    with patch.object(processar_imagem, "ler_qr_code", return_value=[chave_valida]):
        assert enviar(client, headers, b"image").json()["saved"] is True


def test_url_extraida_sem_consulta(client, headers, chave_valida):
    url = f"http://127.0.0.1/consulta?chNFe={chave_valida}"
    with patch.object(processar_imagem, "ler_qr_code", return_value=[url]):
        result = enviar(client, headers, b"image")
    assert result.json()["urls_consulta"] == [url]


def test_outro_sistema_e_escopo_da_instancia(client, headers, imagem_qr):
    primeiro = enviar(client, headers, imagem_qr).json()
    outro = enviar(client, {**headers, "instance": "outra"}, imagem_qr).json()
    outro_sistema = enviar(client, {**headers, "message_id": "manual-1"}, imagem_qr)
    assert primeiro["saved"] and outro["saved"] and outro_sistema.json()["saved"]
    assert not outro["replayed"] and not outro_sistema.json()["replayed"]
    ids = {
        result["submissoes"][0]["submissao_id"]
        for result in [primeiro, outro, outro_sistema.json()]
    }
    assert len(ids) == 3


def test_chave_sem_digito_valido_nao_salva(client, headers, chave_valida):
    invalida = chave_valida[:-1] + str((int(chave_valida[-1]) + 1) % 10)
    with patch.object(processar_imagem, "ler_qr_code", return_value=[invalida]):
        result = enviar(client, headers, b"image")
    assert result.status_code == 200
    assert result.json()["saved"] is False
    assert result.json()["qr_code_found"] is True
    assert result.json()["submissoes"] == []


def test_ocr_e_fallback_exclusivo_quando_qr_nao_tem_chave(
    client, headers, chave_valida
):
    with (
        patch.object(
            processar_imagem,
            "ler_qr_code",
            return_value=["conteudo sem chave"],
        ),
        patch.object(
            processar_imagem,
            "ler_chave_ocr",
            return_value=[chave_valida],
        ) as ocr,
    ):
        resultado_ocr = enviar(client, headers, b"imagem-ocr")

    assert resultado_ocr.status_code == 200
    assert resultado_ocr.json()["saved"] is True
    assert resultado_ocr.json()["qr_code_found"] is True
    ocr.assert_called_once_with(b"imagem-ocr")

    with (
        patch.object(processar_imagem, "ler_qr_code", return_value=[chave_valida]),
        patch.object(
            processar_imagem,
            "ler_chave_ocr",
            side_effect=AssertionError("OCR nao deve rodar com chave do QR"),
        ),
    ):
        resultado_qr = enviar(
            client,
            {**headers, "message_id": "somente-qr"},
            b"imagem-qr",
        )

    assert resultado_qr.status_code == 200
    assert resultado_qr.json()["saved"] is True
