from datetime import date, timedelta
from decimal import Decimal

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.enums.execucao_fase import ExecucaoFase
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
    RegistrarHeartbeatWorkerService,
    RetomarExecucaoWorkerService,
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
    execucao = next(iter(uow.execucoes_store.values()))
    assert execucao.worker_id == "legacy-worker"
    assert execucao.lease_expira_em is not None
    assert execucao.fase_portal == ExecucaoFase.RESERVADA
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
    assert uow.notas_store[nota.id].status == NotaStatus.PENDENTE


def test_heartbeat_renova_lease_e_registra_inicio_do_portal() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRANDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.EM_EXECUCAO,
        worker_id="worker-a",
        lease_expira_em=utc_now() + timedelta(seconds=10),
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao

    output = RegistrarHeartbeatWorkerService(uow, lease_timeout_seconds=120).execute(
        execucao.id,
        worker_id="worker-a",
        fase=ExecucaoFase.PORTAL_INICIADO,
    )

    assert output.fase_portal == ExecucaoFase.PORTAL_INICIADO.value
    assert uow.execucoes_store[execucao.id].efeito_externo_iniciado_em is not None
    assert uow.execucoes_store[execucao.id].lease_expira_em > utc_now()
    assert uow.commits == 1


def test_retomar_mantem_a_mesma_tentativa() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.PAUSADA)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=2,
        status=ExecucaoStatus.PAUSADA,
        fase_portal=ExecucaoFase.PAUSADA,
        worker_id="worker-a",
        lease_expira_em=utc_now() + timedelta(seconds=30),
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao

    output = RetomarExecucaoWorkerService(uow, lease_timeout_seconds=120).execute(
        execucao.id,
        worker_id="worker-a",
    )

    assert output.tentativa == 2
    assert uow.execucoes_store[execucao.id].status == ExecucaoStatus.EM_EXECUCAO
    assert uow.notas_store[nota.id].status == NotaStatus.CADASTRANDO


def test_recupera_execucao_com_efeito_externo_sem_reenfileirar() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRANDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.EM_EXECUCAO,
        fase_portal=ExecucaoFase.PORTAL_INICIADO,
        efeito_externo_iniciado_em=utc_now() - timedelta(minutes=45),
        lease_expira_em=utc_now() - timedelta(minutes=1),
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao

    output = RecuperarExecucoesExpiradasService(uow, timeout_minutes=30).execute()

    assert len(output) == 1
    assert (
        uow.execucoes_store[execucao.id].status
        == ExecucaoStatus.RESULTADO_DESCONHECIDO
    )
    assert uow.notas_store[nota.id].status == NotaStatus.RESULTADO_DESCONHECIDO
    assert not any(
        item.status == NotaStatus.PENDENTE for item in uow.notas_store.values()
    )

    assert RecuperarExecucoesExpiradasService(uow, timeout_minutes=30).execute() == []


def test_resultado_tardio_do_worker_exige_reconciliacao() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.RESULTADO_DESCONHECIDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.RESULTADO_DESCONHECIDO,
        worker_id="worker-a",
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao

    service = RegistrarResultadoCadastroService(uow)
    try:
        service.execute(
            RegistrarResultadoCadastroInput(
                execucao_id=execucao.id,
                status=ExecucaoStatus.SUCESSO,
                worker_id="worker-a",
            ),
        )
    except ResultadoExecucaoConflitanteException:
        pass
    else:
        raise AssertionError("resultado tardio deveria exigir reconciliacao")

    output = service.execute(
        RegistrarResultadoCadastroInput(
            execucao_id=execucao.id,
            status=ExecucaoStatus.SUCESSO,
            mensagem="confirmado no portal",
        ),
    )
    assert output.status == ExecucaoStatus.SUCESSO
    assert uow.notas_store[nota.id].status == NotaStatus.CADASTRADA


def test_worker_pode_isolar_resultado_apos_falha_de_comunicacao() -> None:
    uow = FakeUnitOfWork()
    nota = NotaFiscal(chave=CHAVE, status=NotaStatus.CADASTRANDO)
    execucao = ExecucaoCadastro(
        nota_fiscal_id=nota.id,
        tentativa=1,
        status=ExecucaoStatus.EM_EXECUCAO,
        worker_id="worker-a",
        lease_expira_em=utc_now() + timedelta(seconds=30),
    )
    uow.notas_store[nota.id] = nota
    uow.execucoes_store[execucao.id] = execucao

    output = RegistrarResultadoCadastroService(uow).execute(
        RegistrarResultadoCadastroInput(
            execucao_id=execucao.id,
            status=ExecucaoStatus.RESULTADO_DESCONHECIDO,
            worker_id="worker-a",
            mensagem="resposta perdida do portal",
        ),
    )

    assert output.status == ExecucaoStatus.RESULTADO_DESCONHECIDO
    assert uow.notas_store[nota.id].status == NotaStatus.RESULTADO_DESCONHECIDO
