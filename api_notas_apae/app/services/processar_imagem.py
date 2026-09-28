import hashlib
import json
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError

from app.domain.enums.origem_submissao import OrigemSubmissao
from app.repositories.eventos import EventoImagemRepository
from app.repositories.exceptions import DuplicateKeyError
from app.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.imagem import ProcessarImagemResponse
from app.schemas.registrar_submissao_input import RegistrarSubmissaoInput
from app.schemas.submissao_schemas import RegistrarSubmissaoResponse
from app.services.qr_code import ler_qr_code
from app.services.submissoes import registrar_em_transacao
from app.services.validar_chave import extrair_chave_acesso


class EventoConflitante(Exception):
    pass


class ProcessamentoConcorrente(Exception):
    pass


class ProcessarImagemService:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork):
        self.uow = unit_of_work

    @staticmethod
    def _repetir(evento, fingerprint):
        if evento.fingerprint != fingerprint:
            raise EventoConflitante("Evento reutilizado com conteúdo diferente")
        return ProcessarImagemResponse.model_validate(evento.resultado).model_copy(
            update={"replayed": True},
        )

    def execute(
        self,
        imagem: bytes,
        telefone: str,
        origem: OrigemSubmissao,
        instancia: str,
        evento_id: str,
    ) -> ProcessarImagemResponse:
        metadata = json.dumps([telefone, origem.value, instancia, evento_id]).encode()
        fingerprint = hashlib.sha256(metadata + b"\0" + imagem).hexdigest()
        with self.uow as uow:
            evento = EventoImagemRepository(uow.session).buscar(
                origem.value,
                instancia,
                evento_id,
            )
            if evento is not None:
                return self._repetir(evento, fingerprint)

        # O algoritmo não depende do WhatsApp e não abre as URLs extraídas.
        contents = ler_qr_code(imagem)
        chaves = list(dict.fromkeys(filter(None, map(extrair_chave_acesso, contents))))
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
                    evento = repository.buscar(origem.value, instancia, evento_id)
                    if evento is not None:
                        return self._repetir(evento, fingerprint)
                    evento = repository.reservar(
                        origem.value,
                        instancia,
                        evento_id,
                        fingerprint,
                    )
                    result = ProcessarImagemResponse(
                        saved=bool(chaves),
                        qr_code_found=bool(contents),
                        urls_consulta=urls,
                        reason=None
                        if chaves
                        else "Nenhuma chave fiscal válida no QR Code",
                    )
                    for chave in chaves:
                        output = registrar_em_transacao(
                            uow,
                            RegistrarSubmissaoInput(telefone, origem, chave),
                        )
                        uow.session.flush()
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
