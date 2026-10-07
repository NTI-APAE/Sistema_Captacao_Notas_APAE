import logging
import os
import re
import secrets

from fastapi import FastAPI, HTTPException, Request

from .evolution import EVOLUTION_INSTANCE, recuperar_imagem
from .notas import processar_imagem

logger = logging.getLogger(__name__)
app = FastAPI(title="Captacao WhatsApp - Notas APAE")


@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/webhook/whatsapp")
async def receber_mensagem(request: Request):
    token = os.getenv("EVOLUTION_WEBHOOK_TOKEN")
    if not token:
        raise HTTPException(503, "EVOLUTION_WEBHOOK_TOKEN nao configurado")
    if not secrets.compare_digest(
        request.headers.get("x-webhook-token", "").encode(), token.encode()
    ):
        raise HTTPException(401, "Token invalido")
    try:
        payload = await request.json()
    except ValueError as error:
        raise HTTPException(400, "JSON invalido") from error
    if not isinstance(payload, dict):
        raise HTTPException(400, "O corpo deve ser um objeto JSON")
    if payload.get("event") != "messages.upsert":
        return {"received": True, "ignored": True}

    instance = payload.get("instance")
    if instance != EVOLUTION_INSTANCE:
        return {"received": True, "ignored": True, "reason": "Instancia diferente"}

    data = payload.get("data")
    if not isinstance(data, dict):
        raise HTTPException(400, "Campo data invalido")
    key = data.get("key")
    if not isinstance(key, dict):
        raise HTTPException(400, "Campo key invalido")

    from_me = key.get("fromMe") is True
    message_type = data.get("messageType")
    if not isinstance(message_type, str) or not message_type:
        message_type = None
    logger.info(
        "Evento recebido: messages.upsert",
        extra={
            "event": "messages_upsert",
            "message_type": message_type or "unknown",
        },
    )
    if from_me:
        return {"received": True, "ignored": True, "reason": "Mensagem propria"}

    remote_jid = key.get("remoteJid")
    if not isinstance(remote_jid, str):
        raise HTTPException(400, "Remetente ausente")
    remote_jid_alt = key.get("remoteJidAlt")
    if not isinstance(remote_jid_alt, str) or not remote_jid_alt:
        remote_jid_alt = None
    if remote_jid.endswith(("@g.us", "@broadcast")):
        return {"received": True, "ignored": True}

    # LIDs nao sao telefones. Usar o endereco alternativo apenas se for um PN.
    contact_jid = remote_jid_alt if remote_jid.endswith("@lid") else remote_jid
    if not isinstance(contact_jid, str) or not re.fullmatch(
        r"[0-9]{8,15}@s\.whatsapp\.net", contact_jid
    ):
        return {
            "received": True,
            "ignored": True,
            "reason": "Telefone indisponivel",
        }

    message = data.get("message")
    image_message = message.get("imageMessage") if isinstance(message, dict) else None
    if not isinstance(image_message, dict):
        return {"received": True, "ignored": True, "reason": "Mensagem sem imagem"}

    message_id = key.get("id")
    if not isinstance(message_id, str) or not message_id:
        raise HTTPException(400, "Mensagem sem ID")

    timestamp = data.get("messageTimestamp")
    if not isinstance(timestamp, (str, int)):
        timestamp = None
    push_name = data.get("pushName")
    if not isinstance(push_name, str):
        push_name = None
    mimetype = image_message.get("mimetype")
    if not isinstance(mimetype, str):
        mimetype = None
    caption = image_message.get("caption")
    if not isinstance(caption, str):
        caption = None

    image, recovered_mimetype = await recuperar_imagem(message_id)
    if mimetype is None and recovered_mimetype != "desconhecido":
        mimetype = recovered_mimetype
    logger.info(
        "Imagem recuperada: OK",
        extra={"event": "image_recovered", "result": "ok"},
    )
    return await processar_imagem(
        image,
        message_id=message_id,
        instance=instance,
        remote_jid=remote_jid,
        remote_jid_alt=remote_jid_alt,
        from_me=from_me,
        message_type=message_type,
        timestamp=timestamp,
        push_name=push_name,
        mimetype=mimetype,
        caption=caption,
    )
