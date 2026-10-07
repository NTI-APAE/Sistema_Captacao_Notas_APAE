from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import SessionLocal
from app.repositories.exceptions import DuplicateKeyError

from .execucao_repository import SQLAlchemyExecucaoCadastroRepository
from .nota_repository import SQLAlchemyNotaRepository
from .pessoa_repository import SQLAlchemyPessoaRepository
from .resumo_operacao_leitor_repository import SQLAlchemyResumoOperacaoLeitorRepository
from .submissao_repository import SQLAlchemySubmissaoRepository


class SQLAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.pessoas = SQLAlchemyPessoaRepository(self.session)
        self.notas = SQLAlchemyNotaRepository(self.session)
        self.submissoes = SQLAlchemySubmissaoRepository(self.session)
        self.execucoes = SQLAlchemyExecucaoCadastroRepository(self.session)
        self.resumos_leitor = SQLAlchemyResumoOperacaoLeitorRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        self.session.close()

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateKeyError("Conflito de integridade no banco") from exc

    def rollback(self) -> None:
        self.session.rollback()
