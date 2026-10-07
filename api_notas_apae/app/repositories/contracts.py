from types import TracebackType
from typing import Protocol
from uuid import UUID

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.entities.pessoa import Pessoa
from app.domain.entities.resumo_operacao_leitor import ResumoOperacaoLeitor
from app.domain.entities.submissao_nota import SubmissaoNota
from app.schemas.pagination import ListarNotasFiltro, PaginatedOutput


class PessoaRepositoryContract(Protocol):
    def buscar_por_id(self, pessoa_id: UUID) -> Pessoa | None:
        raise NotImplementedError

    def buscar_por_telefone(self, telefone: str) -> Pessoa | None:
        raise NotImplementedError

    def adicionar(self, pessoa: Pessoa) -> None:
        raise NotImplementedError


class NotaRepositoryContract(Protocol):
    def buscar_por_id(self, nota_id: UUID) -> NotaFiscal | None:
        raise NotImplementedError

    def buscar_por_chave(self, chave: str) -> NotaFiscal | None:
        raise NotImplementedError

    def adicionar(self, nota: NotaFiscal) -> None:
        raise NotImplementedError

    def salvar(self, nota: NotaFiscal) -> None:
        raise NotImplementedError

    def listar(self, filtro: ListarNotasFiltro) -> PaginatedOutput[NotaFiscal]:
        raise NotImplementedError

    def listar_por_pessoa_unicas(self, pessoa_id: UUID) -> list[NotaFiscal]:
        raise NotImplementedError

    def obter_proxima_para_processamento(
        self, max_tentativas: int | None = None
    ) -> NotaFiscal | None:
        raise NotImplementedError


class SubmissaoRepositoryContract(Protocol):
    def buscar_por_id(self, submissao_id: UUID) -> SubmissaoNota | None:
        raise NotImplementedError

    def adicionar(self, submissao: SubmissaoNota) -> None:
        raise NotImplementedError

    def listar_por_nota(self, nota_id: UUID) -> list[SubmissaoNota]:
        raise NotImplementedError

    def listar_por_pessoa(self, pessoa_id: UUID) -> list[SubmissaoNota]:
        raise NotImplementedError
        raise NotImplementedError


class ExecucaoCadastroRepositoryContract(Protocol):
    def buscar_por_id(self, execucao_id: UUID) -> ExecucaoCadastro | None:
        raise NotImplementedError

    def listar_por_nota(self, nota_id: UUID) -> list[ExecucaoCadastro]:
        raise NotImplementedError

    def obter_ultima_tentativa(self, nota_id: UUID) -> int:
        raise NotImplementedError

    def adicionar(self, execucao: ExecucaoCadastro) -> None:
        raise NotImplementedError

    def salvar(self, execucao: ExecucaoCadastro) -> None:
        raise NotImplementedError

    def listar_expiradas_em_execucao(
        self,
        limite_iniciado_em,
    ) -> list[ExecucaoCadastro]:
        raise NotImplementedError


class ResumoOperacaoLeitorRepositoryContract(Protocol):
    def buscar_por_operacao_id(self, operacao_id: UUID) -> ResumoOperacaoLeitor | None:
        raise NotImplementedError

    def adicionar(self, resumo: ResumoOperacaoLeitor) -> None:
        raise NotImplementedError


class Transaction(Protocol):
    pessoas: PessoaRepositoryContract
    notas: NotaRepositoryContract
    submissoes: SubmissaoRepositoryContract
    execucoes: ExecucaoCadastroRepositoryContract
    resumos_leitor: ResumoOperacaoLeitorRepositoryContract

    def __enter__(self) -> "Transaction":
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError
