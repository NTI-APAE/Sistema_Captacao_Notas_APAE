import os
import re
import secrets

from fastapi import FastAPI, HTTPException, Request

from .evolution import EVOLUTION_INSTANCE, recuperar_imagem
from .notas import processar_imagem

app = FastAPI(title="Captação WhatsApp — Notas APAE")


@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/webhook/whatsapp")
async def receber_mensagem(request: Request):
    token = os.getenv("WEBHOOK_TOKEN")
    if not token:
        raise HTTPException(503, "WEBHOOK_TOKEN não configurado")
    if not secrets.compare_digest(
        request.headers.get("x-webhook-token", "").encode(), token.encode()
    ):
        raise HTTPException(401, "Token inválido")
    try:
        payload = await request.json()
    except ValueError as error:
        raise HTTPException(400, "JSON inválido") from error
    if not isinstance(payload, dict):
        raise HTTPException(400, "O corpo deve ser um objeto JSON")
    if payload.get("event") != "messages.upsert":
        return {"received": True, "ignored": True}
    if payload.get("instance") != EVOLUTION_INSTANCE:
        return {"received": True, "ignored": True, "reason": "Instância diferente"}
    data = payload.get("data")
    if not isinstance(data, dict):
        raise HTTPException(400, "Campo data inválido")
    key = data.get("key")
    if not isinstance(key, dict):
        raise HTTPException(400, "Campo key inválido")
    if key.get("fromMe"):
        return {"received": True, "ignored": True}
    jid = key.get("remoteJid")
    if not isinstance(jid, str):
        raise HTTPException(400, "Remetente ausente")
    if jid.endswith(("@g.us", "@broadcast")):
        return {"received": True, "ignored": True}
    # LIDs não são telefones. Usar o endereço alternativo apenas se for um PN.
    if jid.endswith("@lid"):
        jid = key.get("remoteJidAlt", "")
    if not isinstance(jid, str) or not re.fullmatch(
        r"[0-9]{8,15}@s\.whatsapp\.net", jid
    ):
        return {"received": True, "ignored": True, "reason": "Telefone indisponível"}
    message = data.get("message")
    if not isinstance(message, dict) or not isinstance(
        message.get("imageMessage"), dict
    ):
        return {"received": True, "ignored": True, "reason": "Mensagem sem imagem"}
    message_id = key.get("id")
    if not isinstance(message_id, str) or not message_id:
        raise HTTPException(400, "Mensagem sem ID")

    image, _ = await recuperar_imagem(message_id)
    return await processar_imagem(
        image,
        jid.split("@", 1)[0],
        EVOLUTION_INSTANCE,
        message_id,
    )
