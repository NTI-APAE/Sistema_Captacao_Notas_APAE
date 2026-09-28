from uuid import UUID

from app.domain.exceptions.domain_exception import DomainException


class NotaNaoEncontradaException(DomainException):
    def __init__(self, identificador: UUID | str) -> None:
        super().__init__(f"Nota fiscal nao encontrada: {identificador}")
        self.identificador = identificador
