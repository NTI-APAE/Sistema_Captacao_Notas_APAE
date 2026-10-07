from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.enums.nota_status import NotaStatus
from app.domain.exceptions.transicao_status_invalida_exception import (
    TransicaoStatusInvalidaException,
)
from app.domain.services.chave_fiscal_service import ChaveFiscalService
from app.domain.time import utc_now


@dataclass(slots=True)
class NotaFiscal:
    chave: str
    status: NotaStatus = NotaStatus.PENDENTE
    id: UUID = field(default_factory=uuid4)
    mensagem_status: str | None = None
    valor: Decimal | None = None
    data_emissao: date | None = None
    data_cadastro: datetime | None = None
    criado_em: datetime = field(default_factory=utc_now)
    atualizado_em: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.chave = ChaveFiscalService().normalizar_e_validar(self.chave)

    def iniciar_cadastro(self) -> None:
        self._alterar_status(
            NotaStatus.CADASTRANDO,
            permitidos={
                NotaStatus.PENDENTE,
                NotaStatus.ERRO_CADASTRO,
                NotaStatus.IGNORADA,
                NotaStatus.PAUSADA,
            },
        )

    def marcar_cadastrada(
        self,
        valor: Decimal | None,
        data_emissao: date | None,
        data_cadastro: datetime,
    ) -> None:
        self.valor = valor
        self.data_emissao = data_emissao
        self.data_cadastro = data_cadastro
        self.mensagem_status = None
        self._alterar_status(
            NotaStatus.CADASTRADA,
            permitidos={
                NotaStatus.CADASTRANDO,
                NotaStatus.AGUARDANDO_CAPTCHA,
                NotaStatus.PAUSADA,
            },
        )

    def marcar_erro_cadastro(self, mensagem: str | None = None) -> None:
        self.mensagem_status = mensagem
        self._alterar_status(
            NotaStatus.ERRO_CADASTRO,
            permitidos={
                NotaStatus.CADASTRANDO,
                NotaStatus.AGUARDANDO_CAPTCHA,
                NotaStatus.PAUSADA,
            },
        )

    def marcar_duplicada(self, mensagem: str | None = None) -> None:
        self.mensagem_status = mensagem
        self._alterar_status(
            NotaStatus.DUPLICADA,
            permitidos={
                NotaStatus.CADASTRANDO,
                NotaStatus.AGUARDANDO_CAPTCHA,
                NotaStatus.PAUSADA,
            },
        )

    def marcar_ignorada(self, mensagem: str | None = None) -> None:
        self.mensagem_status = mensagem
        self._alterar_status(
            NotaStatus.IGNORADA,
            permitidos={
                NotaStatus.CADASTRANDO,
                NotaStatus.AGUARDANDO_CAPTCHA,
                NotaStatus.PAUSADA,
            },
        )

    def marcar_timeout_cadastro(self, mensagem: str | None = None) -> None:
        self.mensagem_status = mensagem
        self._alterar_status(
            NotaStatus.ERRO_CADASTRO,
            permitidos={NotaStatus.CADASTRANDO},
        )

    def marcar_aguardando_captcha(self, mensagem: str | None = None) -> None:
        self.mensagem_status = mensagem
        self._alterar_status(
            NotaStatus.AGUARDANDO_CAPTCHA,
            permitidos={NotaStatus.CADASTRANDO},
        )

    def pausar(self, mensagem: str | None = None) -> None:
        self.mensagem_status = mensagem
        self._alterar_status(
            NotaStatus.PAUSADA,
            permitidos={NotaStatus.CADASTRANDO, NotaStatus.AGUARDANDO_CAPTCHA},
        )

    def reprocessar(self) -> None:
        self._alterar_status(
            NotaStatus.PENDENTE,
            permitidos={
                NotaStatus.ERRO_CADASTRO,
                NotaStatus.IGNORADA,
                NotaStatus.PAUSADA,
            },
        )
        self.mensagem_status = None

    def _alterar_status(
        self,
        destino: NotaStatus,
        permitidos: set[NotaStatus],
    ) -> None:
        if self.status not in permitidos:
            raise TransicaoStatusInvalidaException(self.status.value, destino.value)
        self.status = destino
        self.atualizado_em = utc_now()
