import pytest

from app.domain.entities.pessoa import Pessoa
from app.domain.enums.nota_status import NotaStatus
from app.domain.enums.origem_submissao import OrigemSubmissao
from app.domain.enums.submissao_status import SubmissaoStatus
from app.domain.exceptions.chave_invalida_exception import ChaveInvalidaException
from app.schemas.registrar_submissao_input import RegistrarSubmissaoInput
from app.services.submissoes import RegistrarSubmissaoService
from tests.fixtures.fakes import FakeUnitOfWork

CHAVE = "21260912345678000123550010001234561234567890"


def test_cadastra_pessoa_nova_e_cria_nota() -> None:
    uow = FakeUnitOfWork()
    output = RegistrarSubmissaoService(uow).execute(
        RegistrarSubmissaoInput(
            telefone="+55 (98) 99999-9999",
            origem=OrigemSubmissao.MANUAL,
            chave=CHAVE,
        ),
    )

    assert output.status == SubmissaoStatus.PENDENTE
    assert output.duplicada is False
    assert len(uow.pessoas_store) == 1
    assert len(uow.notas_store) == 1
    assert len(uow.submissoes_store) == 1
    assert next(iter(uow.pessoas_store.values())).telefone == "5598999999999"
    assert next(iter(uow.notas_store.values())).status == NotaStatus.PENDENTE


def test_reutiliza_pessoa_existente() -> None:
    uow = FakeUnitOfWork()
    pessoa = Pessoa(telefone="5598999999999")
    uow.pessoas_store[pessoa.id] = pessoa

    RegistrarSubmissaoService(uow).execute(
        RegistrarSubmissaoInput(
            telefone="55 98 99999 9999",
            origem=OrigemSubmissao.MANUAL,
            chave=CHAVE,
        ),
    )

    assert len(uow.pessoas_store) == 1


def test_detecta_nota_duplicada_e_preserva_nova_submissao() -> None:
    uow = FakeUnitOfWork()
    service = RegistrarSubmissaoService(uow)
    first = service.execute(
        RegistrarSubmissaoInput("5598999999999", OrigemSubmissao.MANUAL, CHAVE),
    )
    second = service.execute(
        RegistrarSubmissaoInput("5598111111111", OrigemSubmissao.MANUAL, CHAVE),
    )

    assert second.status == SubmissaoStatus.DUPLICADA
    assert second.duplicada is True
    assert second.nota_id == first.nota_id
    assert second.submissao_id != first.submissao_id
    assert len(uow.notas_store) == 1
    assert len(uow.submissoes_store) == 2


@pytest.mark.parametrize(
    "chave",
    [
        "1" * 43,
        "1" * 45,
        "1" * 43 + "A",
    ],
)
def test_rejeita_chave_invalida(chave: str) -> None:
    with pytest.raises(ChaveInvalidaException):
        RegistrarSubmissaoService(FakeUnitOfWork()).execute(
            RegistrarSubmissaoInput("5598999999999", OrigemSubmissao.MANUAL, chave),
        )


def test_trata_concorrencia_por_chave_unica() -> None:
    uow = FakeUnitOfWork()
    service = RegistrarSubmissaoService(uow)
    service.execute(
        RegistrarSubmissaoInput("5598999999999", OrigemSubmissao.MANUAL, CHAVE),
    )
    uow.raise_duplicate_once = True

    output = service.execute(
        RegistrarSubmissaoInput("5598111111111", OrigemSubmissao.MANUAL, CHAVE),
    )

    assert output.duplicada is True
    assert output.status == SubmissaoStatus.DUPLICADA
    assert uow.rollbacks == 1
