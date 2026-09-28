from types import TracebackType
from uuid import UUID

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.entities.pessoa import Pessoa
from app.domain.entities.submissao_nota import SubmissaoNota
from app.domain.enums.execucao_status import ExecucaoStatus
from app.domain.enums.nota_status import NotaStatus
from app.repositories.exceptions import DuplicateKeyError
from app.schemas.pagination import ListarNotasFiltro, PaginatedOutput


class FakePessoaRepository:
    def __init__(self, pessoas: dict[UUID, Pessoa]) -> None:
        self._pessoas = pessoas

    def buscar_por_id(self, pessoa_id: UUID) -> Pessoa | None:
        return self._pessoas.get(pessoa_id)

    def buscar_por_telefone(self, telefone: str) -> Pessoa | None:
        return next(
            (
                pessoa
                for pessoa in self._pessoas.values()
                if pessoa.telefone == telefone
            ),
            None,
        )

    def adicionar(self, pessoa: Pessoa) -> None:
        self._pessoas[pessoa.id] = pessoa


class FakeNotaRepository:
    def __init__(self, notas: dict[UUID, NotaFiscal]) -> None:
        self._notas = notas
        self.submissoes: dict[UUID, SubmissaoNota] = {}

    def buscar_por_id(self, nota_id: UUID) -> NotaFiscal | None:
        return self._notas.get(nota_id)

    def buscar_por_chave(self, chave: str) -> NotaFiscal | None:
        return next(
            (nota for nota in self._notas.values() if nota.chave == chave),
            None,
        )

    def adicionar(self, nota: NotaFiscal) -> None:
        self._notas[nota.id] = nota

    def salvar(self, nota: NotaFiscal) -> None:
        self._notas[nota.id] = nota

    def listar(self, filtro: ListarNotasFiltro) -> PaginatedOutput[NotaFiscal]:
        notas = list(self._notas.values())
        if filtro.status:
            notas = [nota for nota in notas if nota.status == filtro.status]
        if filtro.chave:
            notas = [nota for nota in notas if nota.chave == filtro.chave]
        total = len(notas)
        return PaginatedOutput(
            items=notas[filtro.offset : filtro.offset + filtro.size],
            page=filtro.page,
            size=filtro.size,
            total=total,
        )

    def listar_por_pessoa_unicas(self, pessoa_id: UUID) -> list[NotaFiscal]:
        return [
            nota
            for nota in self._notas.values()
            if any(
                submissao.pessoa_id == pessoa_id and submissao.nota_fiscal_id == nota.id
                for submissao in self.submissoes.values()
            )
        ]

    def obter_proxima_para_processamento(self) -> NotaFiscal | None:
        return next(
            (
                nota
                for nota in sorted(
                    self._notas.values(),
                    key=lambda item: item.criado_em,
                )
                if nota.status == NotaStatus.PENDENTE
            ),
            None,
        )


class FakeSubmissaoRepository:
    def __init__(self, submissoes: dict[UUID, SubmissaoNota]) -> None:
        self._submissoes = submissoes

    def buscar_por_id(self, submissao_id: UUID) -> SubmissaoNota | None:
        return self._submissoes.get(submissao_id)

    def adicionar(self, submissao: SubmissaoNota) -> None:
        self._submissoes[submissao.id] = submissao

    def listar_por_nota(self, nota_id: UUID) -> list[SubmissaoNota]:
        return [
            submissao
            for submissao in self._submissoes.values()
            if submissao.nota_fiscal_id == nota_id
        ]

    def listar_por_pessoa(self, pessoa_id: UUID) -> list[SubmissaoNota]:
        return [
            submissao
            for submissao in self._submissoes.values()
            if submissao.pessoa_id == pessoa_id
        ]


class FakeExecucaoCadastroRepository:
    def __init__(self, execucoes: dict[UUID, ExecucaoCadastro]) -> None:
        self._execucoes = execucoes

    def buscar_por_id(self, execucao_id: UUID) -> ExecucaoCadastro | None:
        return self._execucoes.get(execucao_id)

    def listar_por_nota(self, nota_id: UUID) -> list[ExecucaoCadastro]:
        return [
            execucao
            for execucao in self._execucoes.values()
            if execucao.nota_fiscal_id == nota_id
        ]

    def obter_ultima_tentativa(self, nota_id: UUID) -> int:
        tentativas = [
            execucao.tentativa
            for execucao in self._execucoes.values()
            if execucao.nota_fiscal_id == nota_id
        ]
        return max(tentativas, default=0)

    def adicionar(self, execucao: ExecucaoCadastro) -> None:
        self._execucoes[execucao.id] = execucao

    def salvar(self, execucao: ExecucaoCadastro) -> None:
        self._execucoes[execucao.id] = execucao

    def listar_expiradas_em_execucao(
        self,
        limite_iniciado_em,
    ) -> list[ExecucaoCadastro]:
        return [
            execucao
            for execucao in self._execucoes.values()
            if execucao.status == ExecucaoStatus.EM_EXECUCAO
            and execucao.iniciado_em is not None
            and execucao.iniciado_em < limite_iniciado_em
        ]


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.pessoas_store: dict[UUID, Pessoa] = {}
        self.notas_store: dict[UUID, NotaFiscal] = {}
        self.submissoes_store: dict[UUID, SubmissaoNota] = {}
        self.execucoes_store: dict[UUID, ExecucaoCadastro] = {}
        self.commits = 0
        self.rollbacks = 0
        self.raise_duplicate_once = False

    def __enter__(self) -> "FakeUnitOfWork":
        self.pessoas = FakePessoaRepository(self.pessoas_store)
        self.notas = FakeNotaRepository(self.notas_store)
        self.notas.submissoes = self.submissoes_store
        self.submissoes = FakeSubmissaoRepository(self.submissoes_store)
        self.execucoes = FakeExecucaoCadastroRepository(self.execucoes_store)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        if self.raise_duplicate_once:
            self.raise_duplicate_once = False
            raise DuplicateKeyError("duplicate key")
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
