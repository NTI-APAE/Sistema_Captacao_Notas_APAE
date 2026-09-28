from app.domain.exceptions.domain_exception import DomainException


class TransicaoStatusInvalidaException(DomainException):
    def __init__(self, status_atual: str, status_destino: str) -> None:
        super().__init__(
            f"Transicao de status invalida: {status_atual} -> {status_destino}",
        )
        self.status_atual = status_atual
        self.status_destino = status_destino
