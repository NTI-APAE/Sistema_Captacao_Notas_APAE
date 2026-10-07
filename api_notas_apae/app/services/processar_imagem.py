import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError

from app.domain.entities.pessoa import normalizar_telefone
from app.domain.enums.origem_submissao import OrigemSubmissao
from app.models.submissao_nota_model import SubmissaoNotaModel
from app.repositories.eventos import EventoImagemRepository
from app.repositories.exceptions import DuplicateKeyError
from app.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.imagem import ProcessarImagemResponse
from app.schemas.registrar_submissao_input import RegistrarSubmissaoInput
from app.schemas.submissao_schemas import RegistrarSubmissaoResponse
from app.services.qr_code import ler_chave_ocr, ler_qr_code
from app.services.submissoes import registrar_em_transacao
from app.services.validar_chave import extrair_chave_acesso


class EventoConflitante(Exception):
    pass


class ProcessamentoConcorrente(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ProcessarImagemMetadata:
    message_id: str
    instance: str
    remote_jid: str
    remote_jid_alt: str | None = None
    from_me: bool = False
    message_type: str | None = None
    timestamp: str | None = None
    push_name: str | None = None
    mimetype: str | None = None
    caption: str | None = None


class ProcessarImagemService:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork):
        self.uow = unit_of_work

    @staticmethod
    def _data_mensagem(timestamp: str | None) -> datetime | None:
        if timestamp is None:
            return None
        try:
            value = float(timestamp)
            if value > 10_000_000_000:
                value /= 1000
            return datetime.fromtimestamp(value, UTC)
        except (OverflowError, ValueError):
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                return None

    @staticmethod
    def _repetir(evento, fingerprint):
        if evento.fingerprint != fingerprint:
            raise EventoConflitante("Evento reutilizado com conteúdo diferente")
        evento.reenvios += 1
        evento.ultimo_reenvio_em = datetime.now(UTC)
        return ProcessarImagemResponse.model_validate(evento.resultado).model_copy(
            update={"replayed": True},
        )

    def execute(
        self,
        imagem: bytes,
        metadata: ProcessarImagemMetadata,
    ) -> ProcessarImagemResponse:
        telefone = self._telefone_from_jid(
            metadata.remote_jid,
            metadata.remote_jid_alt,
        )
        origem = OrigemSubmissao.WHATSAPP
        fingerprint_data = json.dumps(
            [
                telefone,
                origem.value,
                metadata.instance,
                metadata.message_id,
                metadata.remote_jid,
                metadata.remote_jid_alt,
            ],
            ensure_ascii=False,
        ).encode()
        fingerprint = hashlib.sha256(fingerprint_data + b"\0" + imagem).hexdigest()
        with self.uow as uow:
            evento = EventoImagemRepository(uow.session).buscar(
                origem.value,
                metadata.instance,
                metadata.message_id,
            )
            if evento is not None:
                result = self._repetir(evento, fingerprint)
                uow.commit()
                return result

        # O algoritmo não depende do WhatsApp e não abre as URLs extraídas.
        contents = ler_qr_code(imagem)
        chaves = list(dict.fromkeys(filter(None, map(extrair_chave_acesso, contents))))
        if not chaves:
            chaves = list(dict.fromkeys(ler_chave_ocr(imagem)))
        urls = []
        for content in contents:
            try:
                url = urlparse(content)
                if (
                    url.scheme in ("http", "https")
                    and url.hostname
                    and content not in urls
                ):
                    urls.append(content)
            except ValueError:
                continue

        for _ in range(3):
            try:
                with self.uow as uow:
                    repository = EventoImagemRepository(uow.session)
                    evento = repository.buscar(
                        origem.value,
                        metadata.instance,
                        metadata.message_id,
                    )
                    if evento is not None:
                        result = self._repetir(evento, fingerprint)
                        uow.commit()
                        return result
                    evento = repository.reservar(
                        origem.value,
                        metadata.instance,
                        metadata.message_id,
                        fingerprint,
                        remote_jid=metadata.remote_jid,
                        remote_jid_alt=metadata.remote_jid_alt,
                        from_me=metadata.from_me,
                        message_type=metadata.message_type,
                        data_mensagem=self._data_mensagem(metadata.timestamp),
                        push_name=metadata.push_name,
                        mimetype=metadata.mimetype,
                        caption=metadata.caption,
                    )
                    result = ProcessarImagemResponse(
                        saved=bool(chaves),
                        qr_code_found=bool(contents),
                        urls_consulta=urls,
                        reason=None
                        if chaves
                        else "Nenhuma chave fiscal válida encontrada na imagem",
                    )
                    for chave in chaves:
                        output = registrar_em_transacao(
                            uow,
                            RegistrarSubmissaoInput(telefone, origem, chave),
                        )
                        uow.session.flush()
                        submissao = uow.session.get(
                            SubmissaoNotaModel,
                            output.submissao_id,
                        )
                        if submissao is not None:
                            submissao.evento_instancia = metadata.instance
                            submissao.evento_id = metadata.message_id
                        result.submissoes.append(
                            RegistrarSubmissaoResponse(
                                status=output.status,
                                duplicada=output.duplicada,
                                nota_id=output.nota_id,
                                submissao_id=output.submissao_id,
                            )
                        )
                    evento.resultado = result.model_dump(mode="json")
                    uow.commit()
                    return result
            except (IntegrityError, DuplicateKeyError):
                # O contexto reverte todo o lote antes de reler o vencedor.
                # Inclui conflitos na pessoa, chave fiscal e identidade do evento.
                continue
        raise ProcessamentoConcorrente("Tente reenviar o mesmo evento")

    @staticmethod
    def _telefone_from_jid(remote_jid: str, remote_jid_alt: str | None) -> str:
        if remote_jid.endswith(("@g.us", "@broadcast")):
            raise ValueError("JID de grupo ou broadcast não pode enviar nota")
        candidate = (
            remote_jid_alt
            if remote_jid.endswith("@lid") and remote_jid_alt
            else remote_jid
        )
        telefone = normalizar_telefone(candidate)
        if not re.fullmatch(r"[0-9]{8,15}", telefone):
            raise ValueError("JID remoto sem telefone identificável")
        return telefone
