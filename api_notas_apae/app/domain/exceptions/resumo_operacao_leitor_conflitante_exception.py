from uuid import UUID

from app.domain.exceptions.domain_exception import DomainException


class ResumoOperacaoLeitorConflitanteException(DomainException):
    def __init__(self, operacao_id: UUID) -> None:
        super().__init__(f"Resumo da operacao do leitor conflitante: {operacao_id}")
        self.operacao_id = operacao_id
