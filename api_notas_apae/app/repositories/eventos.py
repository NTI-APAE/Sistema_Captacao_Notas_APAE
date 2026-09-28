from sqlalchemy.orm import Session

from app.models.evento_imagem import EventoImagem


class EventoImagemRepository:
    def __init__(self, session: Session):
        self.session = session

    def buscar(self, origem: str, instancia: str, evento_id: str):
        return self.session.get(EventoImagem, (origem, instancia, evento_id))

    def reservar(self, origem: str, instancia: str, evento_id: str, fingerprint: str):
        evento = EventoImagem(
            origem=origem,
            instancia=instancia,
            evento_id=evento_id,
            fingerprint=fingerprint,
            resultado={},
        )
        self.session.add(evento)
        # A PK composta arbitra requisições concorrentes, não só a consulta prévia.
        self.session.flush()
        return evento
