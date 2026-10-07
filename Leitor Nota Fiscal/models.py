from dataclasses import dataclass
from datetime import datetime
from typing import Optional


STATUS_PENDENTE = "PENDENTE"
STATUS_CADASTRADA = "CADASTRADA"
STATUS_DUPLICADA = "DUPLICADA"
STATUS_ERRO = "ERRO"
STATUS_IGNORADA = "IGNORADA"
STATUS_AGUARDANDO_CAPTCHA = "AGUARDANDO_CAPTCHA"
STATUS_PAUSADA = "PAUSADA"
STATUS_PROCESSANDO = "PROCESSANDO"

STATUS_VALIDOS = {
    STATUS_PENDENTE,
    STATUS_CADASTRADA,
    STATUS_DUPLICADA,
    STATUS_ERRO,
    STATUS_IGNORADA,
    STATUS_AGUARDANDO_CAPTCHA,
    STATUS_PAUSADA,
    STATUS_PROCESSANDO,
}


@dataclass(frozen=True)
class Nota:
    id: str | int
    chave: str
    status: str
    mensagem: str
    arquivo_origem: str
    data_importacao: Optional[str]
    data_cadastro: Optional[str]
    tentativa: int
    criado_em: Optional[str]
    atualizado_em: Optional[str]
    valor: Optional[float] = None
    tempo_cadastro_segundos: Optional[float] = None
    data_emissao_nota: Optional[str] = None
    execucao_id: Optional[str] = None


@dataclass(frozen=True)
class ProcessamentoTXT:
    caminho_arquivo: str
    total_linhas: int
    total_validas: int
    total_invalidas: int
    total_duplicadas: int
    chaves: list[str]


@dataclass(frozen=True)
class ResultadoImportacao:
    arquivo_id: int
    total_linhas: int
    total_validas: int
    total_invalidas: int
    total_duplicadas: int
    total_inseridas: int
    total_reativadas: int
    total_ja_existentes: int


@dataclass(frozen=True)
class RelatorioDia:
    data: str
    cadastradas: int
    valor_cadastradas: float
    tempo_total_segundos: float
    fora_prazo: int
    valor_fora_prazo: float
    duplicadas: int
    erros: int
    valor_erros: float
    ignoradas: int
    pendentes: int
    total: int


def agora_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")
