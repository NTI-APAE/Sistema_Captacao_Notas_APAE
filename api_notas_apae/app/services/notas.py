import logging
from uuid import UUID

from app.domain.entities.pessoa import normalizar_telefone
from app.domain.exceptions.nota_nao_encontrada_exception import (
    NotaNaoEncontradaException,
)
from app.domain.exceptions.pessoa_nao_encontrada_exception import (
    PessoaNaoEncontradaException,
)
from app.domain.services.chave_fiscal_service import ChaveFiscalService
from app.repositories.contracts import Transaction
from app.schemas.nota_output import NotaOutput
from app.schemas.pagination import ListarNotasFiltro, PaginatedOutput
from app.schemas.submissao_output import SubmissaoOutput


class ConsultarNotaService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work
        self._chave_service = ChaveFiscalService()

    def por_id(self, nota_id: UUID) -> NotaOutput:
        with self._unit_of_work as uow:
            nota = uow.notas.buscar_por_id(nota_id)
            if nota is None:
                raise NotaNaoEncontradaException(nota_id)
            return NotaOutput.from_domain(nota)

    def por_chave(self, chave: str) -> NotaOutput:
        chave = self._chave_service.normalizar_e_validar(chave)
        with self._unit_of_work as uow:
            nota = uow.notas.buscar_por_chave(chave)
            if nota is None:
                raise NotaNaoEncontradaException(chave)
            return NotaOutput.from_domain(nota)


class ListarNotasService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work
        self._chave_service = ChaveFiscalService()

    def execute(self, filtro: ListarNotasFiltro) -> PaginatedOutput[NotaOutput]:
        filtro = self._normalizar_filtro(filtro)
        with self._unit_of_work as uow:
            resultado = uow.notas.listar(filtro)
            return PaginatedOutput(
                items=[NotaOutput.from_domain(nota) for nota in resultado.items],
                page=resultado.page,
                size=resultado.size,
                total=resultado.total,
            )

    def _normalizar_filtro(self, filtro: ListarNotasFiltro) -> ListarNotasFiltro:
        chave = (
            self._chave_service.normalizar_e_validar(filtro.chave)
            if filtro.chave
            else None
        )
        telefone = normalizar_telefone(filtro.telefone) if filtro.telefone else None
        return ListarNotasFiltro(
            page=filtro.page,
            size=filtro.size,
            status=filtro.status,
            data_inicial=filtro.data_inicial,
            data_final=filtro.data_final,
            telefone=telefone,
            chave=chave,
        )


class ListarNotasDaPessoaService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, pessoa_id: UUID) -> list[NotaOutput]:
        with self._unit_of_work as uow:
            if uow.pessoas.buscar_por_id(pessoa_id) is None:
                raise PessoaNaoEncontradaException(pessoa_id)
            return [
                NotaOutput.from_domain(nota)
                for nota in uow.notas.listar_por_pessoa_unicas(pessoa_id)
            ]


class ListarSubmissoesDaNotaService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, nota_id: UUID) -> list[SubmissaoOutput]:
        with self._unit_of_work as uow:
            if uow.notas.buscar_por_id(nota_id) is None:
                raise NotaNaoEncontradaException(nota_id)
            return [
                SubmissaoOutput.from_domain(submissao)
                for submissao in uow.submissoes.listar_por_nota(nota_id)
            ]


class ReprocessarNotaService:
    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work
        self._logger = logging.getLogger(__name__)

    def execute(self, nota_id: UUID) -> NotaOutput:
        with self._unit_of_work as uow:
            nota = uow.notas.buscar_por_id(nota_id)
            if nota is None:
                raise NotaNaoEncontradaException(nota_id)
            nota.reprocessar()
            uow.notas.salvar(nota)
            uow.commit()
            self._logger.info(
                "nota enviada para reprocessamento",
                extra={"nota_id": str(nota.id), "resultado": "pendente"},
            )
            return NotaOutput.from_domain(nota)
