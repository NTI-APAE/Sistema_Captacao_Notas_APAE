import base64
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from EvolutionAPI.evolution import recuperar_imagem
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
        self.env = patch.dict(os.environ, {"EVOLUTION_WEBHOOK_TOKEN": "test-token"})
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
                "pushName": "Ana",
                "messageType": "imageMessage",
                "messageTimestamp": 1710000000,
                "message": {
                    "imageMessage": {
                        "mimetype": "image/png",
                        "caption": "nota fiscal",
                    }
                },
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
    def test_forward_bytes_and_metadata(self, media, process):
        process.side_effect = [RESULT, {**RESULT, "replayed": True}]
        self.assertTrue(self.post().json()["saved"])
        self.assertTrue(self.post().json()["replayed"])
        self.assertEqual(process.await_count, 2)
        for call in process.await_args_list:
            self.assertEqual(call.args, (b"image",))
            self.assertEqual(
                call.kwargs,
                {
                    "message_id": "abc",
                    "instance": EVOLUTION_INSTANCE,
                    "remote_jid": "5598999999999@s.whatsapp.net",
                    "remote_jid_alt": None,
                    "from_me": False,
                    "message_type": "imageMessage",
                    "timestamp": 1710000000,
                    "push_name": "Ana",
                    "mimetype": "image/png",
                    "caption": "nota fiscal",
                },
            )
        self.assertEqual(media.await_count, 2)

    @patch("EvolutionAPI.webhook.processar_imagem", new_callable=AsyncMock)
    @patch(
        "EvolutionAPI.webhook.recuperar_imagem",
        new_callable=AsyncMock,
        return_value=(b"image", "image/png"),
    )
    def test_optional_metadata_can_be_absent(self, media, process):
        self.payload["data"].pop("pushName")
        self.payload["data"].pop("messageType")
        self.payload["data"].pop("messageTimestamp")
        self.payload["data"]["message"]["imageMessage"].pop("mimetype")
        self.payload["data"]["message"]["imageMessage"].pop("caption")
        process.return_value = RESULT

        response = self.post()

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(process.await_args.kwargs["message_type"])
        self.assertIsNone(process.await_args.kwargs["timestamp"])
        self.assertIsNone(process.await_args.kwargs["push_name"])
        self.assertEqual(process.await_args.kwargs["mimetype"], "image/png")
        self.assertIsNone(process.await_args.kwargs["caption"])

    @patch("EvolutionAPI.webhook.processar_imagem", new_callable=AsyncMock)
    @patch("EvolutionAPI.webhook.recuperar_imagem", new_callable=AsyncMock)
    def test_from_me_is_ignored(self, media, process):
        self.payload["data"]["key"]["fromMe"] = True

        response = self.post()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ignored"])
        media.assert_not_awaited()
        process.assert_not_awaited()

    @patch("EvolutionAPI.webhook.recuperar_imagem", new_callable=AsyncMock)
    def test_ignored(self, media):
        for jid in ["123@g.us", "123@broadcast", "123@lid"]:
            self.payload["data"]["key"]["remoteJid"] = jid
            self.assertTrue(self.post().json()["ignored"])
        media.assert_not_awaited()

    @patch("EvolutionAPI.webhook.recuperar_imagem", new_callable=AsyncMock)
    def test_wrong_instance(self, media):
        self.payload["instance"] = "another"

        response = self.post()

        self.assertTrue(response.json()["ignored"])
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
    async def test_multipart_contract_and_failure(self):
        with (
            patch.dict(os.environ, {"NOTAS_API_INTERNAL_KEY": "test-token"}),
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
            result = await processar_imagem(
                b"image",
                message_id="abc",
                instance="teste2",
                remote_jid="5598999999999@s.whatsapp.net",
                message_type="imageMessage",
                timestamp=1710000000,
                push_name="Ana",
                mimetype="image/png",
                caption="nota fiscal",
            )
            self.assertTrue(result["saved"])
            kwargs = client.post.call_args.kwargs
            self.assertNotIn("content", kwargs)
            self.assertEqual(kwargs["data"]["message_id"], "abc")
            self.assertEqual(kwargs["data"]["instance"], "teste2")
            self.assertEqual(
                kwargs["data"]["remote_jid"], "5598999999999@s.whatsapp.net"
            )
            self.assertEqual(kwargs["data"]["from_me"], "false")
            self.assertEqual(kwargs["files"]["imagem"][1], b"image")
            self.assertEqual(kwargs["files"]["imagem"][2], "image/png")
            headers = kwargs["headers"]
            self.assertEqual(headers["X-Internal-API-Key"], "test-token")

            for error, status in [
                (httpx.ConnectError("offline"), 502),
                (httpx.ReadTimeout("timeout"), 504),
            ]:
                client.post.side_effect = error
                with self.assertRaises(HTTPException) as raised:
                    await processar_imagem(
                        b"image",
                        message_id="abc",
                        instance="teste2",
                        remote_jid="5598999999999@s.whatsapp.net",
                    )
                self.assertEqual(raised.exception.status_code, status)

    async def test_optional_fields_are_omitted_from_multipart(self):
        with (
            patch.dict(os.environ, {"NOTAS_API_INTERNAL_KEY": "test-token"}),
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

            await processar_imagem(
                b"image",
                message_id="abc",
                instance="teste2",
                remote_jid="5598999999999@s.whatsapp.net",
            )

            data = client.post.call_args.kwargs["data"]
            self.assertNotIn("caption", data)
            self.assertNotIn("push_name", data)
            self.assertEqual(data["from_me"], "false")

    async def test_rejected_and_malformed_response(self):
        with (
            patch.dict(os.environ, {"NOTAS_API_INTERNAL_KEY": "test-token"}),
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
                    await processar_imagem(
                        b"image",
                        message_id="abc",
                        instance="teste2",
                        remote_jid="5598999999999@s.whatsapp.net",
                    )
                self.assertEqual(raised.exception.status_code, expected)

    async def test_business_result_without_qr_is_success(self):
        no_qr = {**RESULT, "saved": False, "qr_code_found": False, "submissoes": []}
        with (
            patch.dict(os.environ, {"NOTAS_API_INTERNAL_KEY": "test-token"}),
            patch("EvolutionAPI.notas.httpx.AsyncClient") as factory,
        ):
            client = factory.return_value.__aenter__.return_value
            client.post = AsyncMock(
                return_value=httpx.Response(
                    200,
                    json=no_qr,
                    request=httpx.Request("POST", "http://api/notas/processar-imagem"),
                )
            )

            result = await processar_imagem(
                b"image",
                message_id="abc",
                instance="teste2",
                remote_jid="5598999999999@s.whatsapp.net",
            )

            self.assertFalse(result["saved"])


class EvolutionMediaTests(unittest.IsolatedAsyncioTestCase):
    async def test_recovery_endpoint_and_bytes_are_preserved(self):
        encoded = base64.b64encode(b"image").decode()
        with (
            patch("EvolutionAPI.evolution.EVOLUTION_API_KEY", "evolution-secret"),
            patch("EvolutionAPI.evolution.httpx.AsyncClient") as factory,
        ):
            client = factory.return_value.__aenter__.return_value
            client.post = AsyncMock(
                return_value=httpx.Response(
                    200,
                    json={"base64": encoded, "mimetype": "image/png"},
                    request=httpx.Request("POST", "http://evolution/media"),
                )
            )

            image, mimetype = await recuperar_imagem("abc")

            self.assertEqual(image, b"image")
            self.assertEqual(mimetype, "image/png")
            kwargs = client.post.call_args.kwargs
            self.assertEqual(kwargs["headers"], {"apikey": "evolution-secret"})
            self.assertEqual(
                kwargs["json"],
                {
                    "message": {"key": {"id": "abc"}},
                    "convertToMp4": False,
                },
            )


if __name__ == "__main__":
    unittest.main()
