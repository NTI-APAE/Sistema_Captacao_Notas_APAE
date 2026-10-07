from pathlib import Path
from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models.submissao_nota_model import SubmissaoNotaModel


def test_resposta_perdida_apos_commit_nao_duplica(
    client,
    session_factory,
    imagem_qr,
    monkeypatch,
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4]))
    from EvolutionAPI import notas, webhook

    monkeypatch.setenv("EVOLUTION_WEBHOOK_TOKEN", "test-token")
    monkeypatch.setenv("NOTAS_API_INTERNAL_KEY", "test-internal")
    monkeypatch.setattr(
        webhook,
        "recuperar_imagem",
        AsyncMock(
            return_value=(imagem_qr, "image/png"),
        ),
    )
    transport = httpx.ASGITransport(app=client.app)
    calls = 0

    async def responder(request):
        nonlocal calls
        response = await transport.handle_async_request(request)
        await response.aread()
        calls += 1
        if calls == 1:
            assert response.status_code == 200
            raise httpx.ReadTimeout("Resposta perdida depois do commit")
        return response

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        notas.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(responder),
            **kwargs,
        ),
    )
    webhook_client = TestClient(webhook.app)
    payload = {
        "event": "messages.upsert",
        "instance": webhook.EVOLUTION_INSTANCE,
        "data": {
            "key": {
                "id": "msg-lost",
                "remoteJid": "5598999999999@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"imageMessage": {}},
        },
    }

    def enviar():
        return webhook_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={
                "X-Webhook-Token": "test-token",
            },
        )

    assert enviar().status_code == 504
    retry = enviar()
    assert retry.status_code == 200
    assert retry.json()["replayed"] is True
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(SubmissaoNotaModel)) == 1
