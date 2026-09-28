from dataclasses import dataclass

from app.domain.enums.origem_submissao import OrigemSubmissao


@dataclass(frozen=True, slots=True)
class RegistrarSubmissaoInput:
    telefone: str
    origem: OrigemSubmissao
    chave: str
