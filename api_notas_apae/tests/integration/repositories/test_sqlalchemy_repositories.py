from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.pessoa import Pessoa
from app.domain.enums.origem_submissao import OrigemSubmissao
from app.models.nota_fiscal_model import (
    NotaFiscalModel,
)
from app.models.pessoa_model import PessoaModel
from app.repositories.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from app.schemas.registrar_submissao_input import RegistrarSubmissaoInput
from app.services.submissoes import RegistrarSubmissaoService

CHAVE = "21260912345678000123550010001234561234567890"


def test_unique_chave_no_banco(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(
            NotaFiscalModel(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                chave=CHAVE,
                status="PENDENTE",
            ),
        )
        session.add(
            NotaFiscalModel(
                id=UUID("22222222-2222-2222-2222-222222222222"),
                chave=CHAVE,
                status="PENDENTE",
            ),
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_unit_of_work_preserva_somente_uma_nota_e_duas_submissoes(
    session_factory: sessionmaker[Session],
) -> None:
    service = RegistrarSubmissaoService(SQLAlchemyUnitOfWork(session_factory))
    first = service.execute(
        RegistrarSubmissaoInput("5598999999999", OrigemSubmissao.MANUAL, CHAVE),
    )
    second = service.execute(
        RegistrarSubmissaoInput("5598111111111", OrigemSubmissao.MANUAL, CHAVE),
    )

    assert first.nota_id == second.nota_id
    assert second.duplicada is True

    with session_factory() as session:
        assert session.query(NotaFiscalModel).count() == 1


def test_unit_of_work_faz_rollback_automatico(
    session_factory: sessionmaker[Session],
) -> None:
    uow = SQLAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError):
        with uow:
            uow.pessoas.adicionar(Pessoa(telefone="5598000000000"))
            raise RuntimeError("falha antes do commit")

    with session_factory() as session:
        assert session.query(PessoaModel).count() == 0
