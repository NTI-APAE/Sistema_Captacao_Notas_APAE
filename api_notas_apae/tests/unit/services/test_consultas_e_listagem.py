from uuid import uuid4

import pytest

from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.enums.nota_status import NotaStatus
from app.domain.exceptions.nota_nao_encontrada_exception import (
    NotaNaoEncontradaException,
)
from app.schemas.pagination import ListarNotasFiltro
from app.services.notas import ConsultarNotaService, ListarNotasService
from tests.fixtures.fakes import FakeUnitOfWork

CHAVE = "21260912345678000123550010001234561234567890"
CHAVE_2 = "21260912345678000123550010001234561234567891"


def test_consultar_nota_encontrada() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE)
    uow.notas_store[nota.id] = nota

    output = ConsultarNotaService(uow).por_id(nota.id)

    assert output.id == nota.id
    assert output.chave == CHAVE


def test_consultar_nota_inexistente() -> None:
    with pytest.raises(NotaNaoEncontradaException):
        ConsultarNotaService(FakeUnitOfWork()).por_id(uuid4())


def test_listar_notas_com_paginacao() -> None:
    uow = FakeUnitOfWork()
    uow.notas_store[uuid4()] = NotaFiscal(chave=CHAVE)
    uow.notas_store[uuid4()] = NotaFiscal(chave=CHAVE_2)

    output = ListarNotasService(uow).execute(ListarNotasFiltro(page=2, size=1))

    assert output.page == 2
    assert output.size == 1
    assert output.total == 2
    assert len(output.items) == 1


def test_listar_notas_filtra_por_status_e_chave() -> None:
    uow = FakeUnitOfWork()
    uow.notas_store[uuid4()] = NotaFiscal(chave=CHAVE, status=NotaStatus.PENDENTE)
    uow.notas_store[uuid4()] = NotaFiscal(
        chave=CHAVE_2,
        status=NotaStatus.ERRO_CADASTRO,
    )

    output = ListarNotasService(uow).execute(
        ListarNotasFiltro(status=NotaStatus.ERRO_CADASTRO, chave=CHAVE_2),
    )

    assert output.total == 1
    assert output.items[0].status == NotaStatus.ERRO_CADASTRO
    assert output.items[0].chave == CHAVE_2
