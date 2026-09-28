from app.domain.exceptions.domain_exception import DomainException


class ResultadoExecucaoConflitanteException(DomainException):
    def __init__(self) -> None:
        super().__init__("Resultado conflitante para execucao ja finalizada.")
