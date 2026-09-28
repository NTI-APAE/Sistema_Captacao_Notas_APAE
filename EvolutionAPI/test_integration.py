import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from EvolutionAPI.notas import processar_imagem
from EvolutionAPI.webhook import EVOLUTION_INSTANCE, app

RESULT = {
    "received": True,
    "saved": True,
    "replayed": False,
    "submissoes": [
        {"nota_id": "n", "submissao_id": "s", "duplicada": False, "status": "PENDENTE"}
    ],
}


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"WEBHOOK_TOKEN": "test-token"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(app)
        self.payload = {
            "event": "messages.upsert",
            "instance": EVOLUTION_INSTANCE,
            "data": {
                "key": {
                    "id": "abc",
                    "remoteJid": "5598999999999@s.whatsapp.net",
                    "fromMe": False,
                },
                "message": {"imageMessage": {}},
            },
        }

    def post(self):
        return self.client.post(
            "/webhook/whatsapp",
            json=self.payload,
            headers={"x-webhook-token": "test-token"},
        )

    def test_auth(self):
        self.assertEqual(
            self.client.post("/webhook/whatsapp", json=self.payload).status_code, 401
        )

    @patch("EvolutionAPI.webhook.processar_imagem", new_callable=AsyncMock)
    @patch(
        "EvolutionAPI.webhook.recuperar_imagem",
        new_callable=AsyncMock,
        return_value=(b"image", "image/png"),
    )
    def test_forward_bytes_and_replay(self, media, process):
        process.side_effect = [RESULT, {**RESULT, "replayed": True}]
        self.assertTrue(self.post().json()["saved"])
        self.assertTrue(self.post().json()["replayed"])
        self.assertEqual(process.await_count, 2)
        for call in process.await_args_list:
            self.assertEqual(
                call.args, (b"image", "5598999999999", EVOLUTION_INSTANCE, "abc")
            )

    @patch("EvolutionAPI.webhook.recuperar_imagem", new_callable=AsyncMock)
    def test_ignored(self, media):
        for jid in ["123@g.us", "123@broadcast", "123@lid"]:
            self.payload["data"]["key"]["remoteJid"] = jid
            self.assertTrue(self.post().json()["ignored"])
        media.assert_not_awaited()

    @patch("EvolutionAPI.webhook.recuperar_imagem", new_callable=AsyncMock)
    def test_own_and_wrong_instance(self, media):
        self.payload["data"]["key"]["fromMe"] = True
        self.assertTrue(self.post().json()["ignored"])
        self.payload["data"]["key"]["fromMe"] = False
        self.payload["instance"] = "another"
        self.assertTrue(self.post().json()["ignored"])
        media.assert_not_awaited()

    @patch(
        "EvolutionAPI.webhook.processar_imagem",
        new_callable=AsyncMock,
        side_effect=HTTPException(502, "offline"),
    )
    @patch(
        "EvolutionAPI.webhook.recuperar_imagem",
        new_callable=AsyncMock,
        return_value=(b"image", "image/png"),
    )
    def test_failure_not_acknowledged(self, media, process):
        self.assertEqual(self.post().status_code, 502)
        process.side_effect = None
        process.return_value = RESULT
        self.assertTrue(self.post().json()["saved"])


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_contract_and_failure(self):
        with (
            patch.dict(os.environ, {"WEBHOOK_TOKEN": "test-token"}),
            patch("EvolutionAPI.notas.httpx.AsyncClient") as factory,
        ):
            client = factory.return_value.__aenter__.return_value
            client.post = AsyncMock(
                return_value=httpx.Response(
                    200,
                    json=RESULT,
                    request=httpx.Request("POST", "http://api/notas/processar-imagem"),
                )
            )
            result = await processar_imagem(b"image", "5598999999999", "teste2", "abc")
            self.assertTrue(result["saved"])
            self.assertEqual(client.post.call_args.kwargs["content"], b"image")
            headers = client.post.call_args.kwargs["headers"]
            self.assertEqual(headers["X-Evento-ID"], "abc")
            self.assertEqual(headers["X-Origem"], "WHATSAPP")
            for error, status in [
                (httpx.ConnectError("offline"), 502),
                (httpx.ReadTimeout("timeout"), 504),
            ]:
                client.post.side_effect = error
                with self.assertRaises(HTTPException) as raised:
                    await processar_imagem(b"image", "5598999999999", "teste2", "abc")
                self.assertEqual(raised.exception.status_code, status)

    async def test_rejected_and_malformed_response(self):
        with (
            patch.dict(os.environ, {"WEBHOOK_TOKEN": "test-token"}),
            patch("EvolutionAPI.notas.httpx.AsyncClient") as factory,
        ):
            client = factory.return_value.__aenter__.return_value
            for status, body, expected in [
                (422, {}, 422),
                (409, {}, 409),
                (401, {}, 502),
                (503, {}, 502),
                (200, {}, 502),
            ]:
                client.post = AsyncMock(
                    return_value=httpx.Response(
                        status,
                        json=body,
                        request=httpx.Request(
                            "POST", "http://api/notas/processar-imagem"
                        ),
                    )
                )
                with self.assertRaises(HTTPException) as raised:
                    await processar_imagem(b"image", "5598999999999", "teste2", "abc")
                self.assertEqual(raised.exception.status_code, expected)


if __name__ == "__main__":
    unittest.main()
