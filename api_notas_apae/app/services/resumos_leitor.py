from app.domain.entities.resumo_operacao_leitor import ResumoOperacaoLeitor
from app.domain.exceptions.resumo_operacao_leitor_conflitante_exception import (
    ResumoOperacaoLeitorConflitanteException,
)
from app.repositories.contracts import Transaction
from app.repositories.exceptions import DuplicateKeyError
from app.schemas.resumo_operacao_leitor import RegistrarResumoOperacaoLeitorRequest


class RegistrarResumoOperacaoLeitorService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        data: RegistrarResumoOperacaoLeitorRequest,
    ) -> ResumoOperacaoLeitor:
        novo = ResumoOperacaoLeitor(**data.model_dump())
        with self._unit_of_work as uow:
            existente = uow.resumos_leitor.buscar_por_operacao_id(novo.operacao_id)
            if existente:
                if not existente.mesmos_dados(novo):
                    raise ResumoOperacaoLeitorConflitanteException(novo.operacao_id)
                return existente
            uow.resumos_leitor.adicionar(novo)
            try:
                uow.commit()
            except DuplicateKeyError:
                existente = uow.resumos_leitor.buscar_por_operacao_id(novo.operacao_id)
                if existente and existente.mesmos_dados(novo):
                    return existente
                raise ResumoOperacaoLeitorConflitanteException(
                    novo.operacao_id
                ) from None
            return novo
