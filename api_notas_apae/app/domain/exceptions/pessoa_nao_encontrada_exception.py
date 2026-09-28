from uuid import UUID

from app.domain.exceptions.domain_exception import DomainException


class PessoaNaoEncontradaException(DomainException):
    def __init__(self, identificador: UUID | str) -> None:
        super().__init__(f"Pessoa nao encontrada: {identificador}")
        self.identificador = identificador
