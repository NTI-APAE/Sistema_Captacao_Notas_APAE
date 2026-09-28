from uuid import UUID

from app.domain.entities.pessoa import normalizar_telefone
from app.domain.exceptions.pessoa_nao_encontrada_exception import (
    PessoaNaoEncontradaException,
)
from app.repositories.contracts import Transaction
from app.schemas.pessoa_output import PessoaOutput


class ConsultarPessoaService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def por_id(self, pessoa_id: UUID) -> PessoaOutput:
        with self._unit_of_work as uow:
            pessoa = uow.pessoas.buscar_por_id(pessoa_id)
            if pessoa is None:
                raise PessoaNaoEncontradaException(pessoa_id)
            return PessoaOutput.from_domain(pessoa)

    def por_telefone(self, telefone: str) -> PessoaOutput:
        telefone = normalizar_telefone(telefone)
        with self._unit_of_work as uow:
            pessoa = uow.pessoas.buscar_por_telefone(telefone)
            if pessoa is None:
                raise PessoaNaoEncontradaException(telefone)
            return PessoaOutput.from_domain(pessoa)
