from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportarNotasInput:
    nome_arquivo: str
    total_linhas: int
    total_invalidas: int
    total_duplicadas_txt: int
    chaves: list[str]
