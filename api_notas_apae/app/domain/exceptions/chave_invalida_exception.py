from app.domain.exceptions.domain_exception import DomainException


class ChaveInvalidaException(DomainException):
    def __init__(self, chave: str) -> None:
        super().__init__("A chave fiscal deve conter exatamente 44 digitos numericos.")
        self.chave = chave
