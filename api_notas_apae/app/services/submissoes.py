import logging

from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.entities.pessoa import Pessoa, normalizar_telefone
from app.domain.entities.submissao_nota import SubmissaoNota
from app.domain.enums.submissao_status import SubmissaoStatus
from app.domain.services.chave_fiscal_service import ChaveFiscalService
from app.repositories.contracts import Transaction
from app.repositories.exceptions import DuplicateKeyError
from app.schemas.registrar_submissao_input import RegistrarSubmissaoInput
from app.schemas.registrar_submissao_output import RegistrarSubmissaoOutput


def registrar_em_transacao(
    uow: Transaction, data: RegistrarSubmissaoInput
) -> RegistrarSubmissaoOutput:
    """Regras compartilhadas; o chamador controla commit/rollback do lote."""
    telefone = normalizar_telefone(data.telefone)
    chave = ChaveFiscalService().normalizar_e_validar(data.chave)
    pessoa = uow.pessoas.buscar_por_telefone(telefone)
    if pessoa is None:
        pessoa = Pessoa(telefone=telefone)
        uow.pessoas.adicionar(pessoa)

    nota = uow.notas.buscar_por_chave(chave)
    duplicada = nota is not None
    if nota is None:
        nota = NotaFiscal(chave=chave)
        uow.notas.adicionar(nota)

    submissao = SubmissaoNota(
        pessoa_id=pessoa.id,
        origem=data.origem,
        nota_fiscal_id=nota.id,
        chave_extraida=chave,
        status=(SubmissaoStatus.DUPLICADA if duplicada else SubmissaoStatus.PENDENTE),
    )
    uow.submissoes.adicionar(submissao)

    return RegistrarSubmissaoOutput(
        status=submissao.status,
        duplicada=duplicada,
        nota_id=nota.id,
        submissao_id=submissao.id,
    )


class RegistrarSubmissaoService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, data: RegistrarSubmissaoInput) -> RegistrarSubmissaoOutput:
        for _ in range(3):
            with self._unit_of_work as uow:
                output = registrar_em_transacao(uow, data)
                try:
                    uow.commit()
                except DuplicateKeyError:
                    # Outra transação pode ter criado a pessoa OU a nota.
                    uow.rollback()
                    continue
                logging.getLogger(__name__).info("submissao registrada")
                return output
        raise DuplicateKeyError("Conflito concorrente ao registrar submissao")
