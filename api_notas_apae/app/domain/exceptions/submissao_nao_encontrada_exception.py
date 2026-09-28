from uuid import UUID

from app.domain.exceptions.domain_exception import DomainException


class SubmissaoNaoEncontradaException(DomainException):
    def __init__(self, submissao_id: UUID) -> None:
        super().__init__(f"Submissao nao encontrada: {submissao_id}")
        self.submissao_id = submissao_id
