from datetime import datetime

from sqlalchemy.orm import Session

from app.models.evento_imagem import EventoImagem


class EventoImagemRepository:
    def __init__(self, session: Session):
        self.session = session

    def buscar(self, origem: str, instancia: str, evento_id: str):
        return self.session.get(EventoImagem, (origem, instancia, evento_id))

    def reservar(
        self,
        origem: str,
        instancia: str,
        evento_id: str,
        fingerprint: str,
        *,
        remote_jid: str | None = None,
        remote_jid_alt: str | None = None,
        from_me: bool = False,
        message_type: str | None = None,
        data_mensagem: datetime | None = None,
        push_name: str | None = None,
        mimetype: str | None = None,
        caption: str | None = None,
    ):
        evento = EventoImagem(
            origem=origem,
            instancia=instancia,
            evento_id=evento_id,
            fingerprint=fingerprint,
            resultado={},
            remote_jid=remote_jid,
            remote_jid_alt=remote_jid_alt,
            from_me=from_me,
            message_type=message_type,
            data_mensagem=data_mensagem,
            push_name=push_name,
            mimetype=mimetype,
            caption=caption,
        )
        self.session.add(evento)
        # A PK composta arbitra requisições concorrentes, não só a consulta prévia.
        self.session.flush()
        return evento
