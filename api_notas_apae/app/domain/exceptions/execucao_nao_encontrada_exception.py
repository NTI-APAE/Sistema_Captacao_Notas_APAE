from uuid import UUID

from app.domain.exceptions.domain_exception import DomainException


class ExecucaoNaoEncontradaException(DomainException):
    def __init__(self, execucao_id: UUID) -> None:
        super().__init__(f"Execucao de cadastro nao encontrada: {execucao_id}")
        self.execucao_id = execucao_id
