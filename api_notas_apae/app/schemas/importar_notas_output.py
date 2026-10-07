from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportarNotasOutput:
    total_linhas: int
    total_validas: int
    total_invalidas: int
    total_duplicadas: int
    total_inseridas: int
    total_reativadas: int
    total_ja_existentes: int
