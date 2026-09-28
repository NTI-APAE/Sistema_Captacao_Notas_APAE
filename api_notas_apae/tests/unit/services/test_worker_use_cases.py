from datetime import date, timedelta
from decimal import Decimal

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.enums.execucao_status import ExecucaoStatus
from app.domain.enums.nota_status import NotaStatus
from app.domain.exceptions.resultado_execucao_conflitante_exception import (
    ResultadoExecucaoConflitanteException,
)
from app.domain.time import utc_now
from app.schemas.execucao_cadastro_input import (
    RegistrarResultadoCadastroInput,
)
from app.services.execucoes import (
    RegistrarResultadoCadastroService,
)
from app.services.worker import (
    ObterProximaNotaParaProcessamentoService,
    RecuperarExecucoesExpiradasService,
)
from tests.fixtures.fakes import FakeUnitOfWork

CHAVE = "21260912345678000123550010001234561234567890"
CHAVE_2 = "21260912345678000123550010001234561234567891"


def test_claim_retorna_none_sem_pendentes() -> None:
    output = ObterProximaNotaParaProcessamentoService(FakeUnitOfWork()).execute()

    assert output is None


def test_claim_reserva_nota_pendente_e_cria_execucao() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE)
    uow.notas_store[nota.id] = nota

    output = ObterProximaNotaParaProcessamentoService(uow).execute()

    assert output is not None
    assert output.nota_id == nota.id
    assert output.chave == CHAVE
    assert output.tentativa == 1
    assert uow.notas_store[nota.id].status == NotaStatus.CADASTRANDO
    assert len(uow.execucoes_store) == 1
    assert uow.commits == 1


def test_claim_usa_tentativa_incremental() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE)
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[nota.id] = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.ERRO,
    )

    output = ObterProximaNotaParaProcessamentoService(uow).execute()

    assert output is not None
    assert output.tentativa == 2


def test_resultado_sucesso_repetido_e_idempotente() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRANDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.EM_EXECUCAO,
        iniciado_em=utc_now(),
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao
    data = RegistrarResultadoCadastroInput(
        execucao_id=execucao.id,
        status=ExecucaoStatus.SUCESSO,
        mensagem="ok",
    )

    first = RegistrarResultadoCadastroService(uow).execute(data)
    second = RegistrarResultadoCadastroService(uow).execute(data)

    assert first.status == ExecucaoStatus.SUCESSO
    assert second.status == ExecucaoStatus.SUCESSO
    assert uow.notas_store[nota.id].status == NotaStatus.CADASTRADA


def test_resultado_sucesso_depois_erro_gera_conflito() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRANDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.EM_EXECUCAO,
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao
    service = RegistrarResultadoCadastroService(uow)
    service.execute(
        RegistrarResultadoCadastroInput(
            execucao_id=execucao.id,
            status=ExecucaoStatus.SUCESSO,
            mensagem="ok",
        ),
    )

    try:
        service.execute(
            RegistrarResultadoCadastroInput(
                execucao_id=execucao.id,
                status=ExecucaoStatus.ERRO,
                mensagem="erro",
            ),
        )
    except ResultadoExecucaoConflitanteException:
        pass
    else:
        raise AssertionError("resultado conflitante deveria falhar")


def test_resultado_sucesso_repetido_com_dados_diferentes_gera_conflito() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRANDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.EM_EXECUCAO,
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao
    service = RegistrarResultadoCadastroService(uow)
    service.execute(
        RegistrarResultadoCadastroInput(
            execucao_id=execucao.id,
            status=ExecucaoStatus.SUCESSO,
            mensagem="ok",
            valor=Decimal("10.00"),
            data_emissao=date(2026, 8, 30),
        ),
    )

    try:
        service.execute(
            RegistrarResultadoCadastroInput(
                execucao_id=execucao.id,
                status=ExecucaoStatus.SUCESSO,
                mensagem="ok",
                valor=Decimal("11.00"),
                data_emissao=date(2026, 8, 30),
            ),
        )
    except ResultadoExecucaoConflitanteException:
        pass
    else:
        raise AssertionError("resultado final com dados diferentes deveria falhar")


def test_recupera_execucao_antiga_por_timeout() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRANDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.EM_EXECUCAO,
        iniciado_em=utc_now() - timedelta(minutes=60),
    )
    recente = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=2,
        status=ExecucaoStatus.EM_EXECUCAO,
        iniciado_em=utc_now(),
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao
    uow.execucoes_store[recente.id] = recente

    output = RecuperarExecucoesExpiradasService(uow, timeout_minutes=30).execute()

    assert len(output) == 1
    assert uow.execucoes_store[execucao.id].status == ExecucaoStatus.ERRO
    assert uow.execucoes_store[recente.id].status == ExecucaoStatus.EM_EXECUCAO
    assert uow.notas_store[nota.id].status == NotaStatus.ERRO_CADASTRO
