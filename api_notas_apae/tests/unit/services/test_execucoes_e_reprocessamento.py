from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.enums.execucao_status import ExecucaoStatus
from app.domain.enums.nota_status import NotaStatus
from app.domain.exceptions.transicao_status_invalida_exception import (
    TransicaoStatusInvalidaException,
)
from app.schemas.execucao_cadastro_input import (
    RegistrarResultadoCadastroInput,
)
from app.services.execucoes import (
    IniciarExecucaoCadastroService,
    RegistrarResultadoCadastroService,
)
from app.services.notas import ReprocessarNotaService
from tests.fixtures.fakes import FakeUnitOfWork

CHAVE = "21260912345678000123550010001234561234567890"


def test_iniciar_primeira_e_segunda_tentativa() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE)
    uow.notas_store[nota.id] = nota
    service = IniciarExecucaoCadastroService(uow)

    first = service.execute(nota.id)
    uow.notas_store[nota.id].marcar_erro_cadastro("falha")
    second = service.execute(nota.id)

    assert first.tentativa == 1
    assert second.tentativa == 2
    assert len(uow.execucoes_store) == 2


def test_registrar_resultado_sucesso_atualiza_nota_e_execucao() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE)
    uow.notas_store[nota.id] = nota
    execucao = IniciarExecucaoCadastroService(uow).execute(nota.id)

    output = RegistrarResultadoCadastroService(uow).execute(
        RegistrarResultadoCadastroInput(
            nota_id=nota.id,
            execucao_id=execucao.id,
            status=ExecucaoStatus.SUCESSO,
            valor=Decimal("10.50"),
            data_emissao=date(2026, 9, 1),
        ),
    )

    assert output.status == ExecucaoStatus.SUCESSO
    assert uow.notas_store[nota.id].status == NotaStatus.CADASTRADA
    assert uow.notas_store[nota.id].valor == Decimal("10.50")


@pytest.mark.parametrize(
    ("resultado", "status_nota"),
    [
        (ExecucaoStatus.ERRO, NotaStatus.ERRO_CADASTRO),
        (ExecucaoStatus.AGUARDANDO_CAPTCHA, NotaStatus.AGUARDANDO_CAPTCHA),
        (ExecucaoStatus.PAUSADA, NotaStatus.PAUSADA),
    ],
)
def test_registrar_resultados_alternativos(
    resultado: ExecucaoStatus,
    status_nota: NotaStatus,
) -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE)
    uow.notas_store[nota.id] = nota
    execucao = IniciarExecucaoCadastroService(uow).execute(nota.id)

    RegistrarResultadoCadastroService(uow).execute(
        RegistrarResultadoCadastroInput(
            nota_id=nota.id,
            execucao_id=execucao.id,
            status=resultado,
            mensagem="resultado",
        ),
    )

    assert uow.notas_store[nota.id].status == status_nota


def test_reprocessa_nota_com_erro_para_pendente() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.ERRO_CADASTRO)
    uow.notas_store[nota.id] = nota

    output = ReprocessarNotaService(uow).execute(nota.id)

    assert output.status == NotaStatus.PENDENTE


def test_nao_reprocessa_nota_cadastrada() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRADA)
    uow.notas_store[nota.id] = nota

    with pytest.raises(TransicaoStatusInvalidaException):
        ReprocessarNotaService(uow).execute(nota.id)


def test_transicao_invalida_e_bloqueada() -> None:
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.PENDENTE)

    with pytest.raises(TransicaoStatusInvalidaException):
        nota.marcar_cadastrada(None, None, nota.criado_em)
