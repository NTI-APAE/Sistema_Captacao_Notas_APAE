from dataclasses import dataclass
from datetime import date

from app.domain.enums.nota_status import NotaStatus


@dataclass(frozen=True, slots=True)
class ListarNotasFiltro:
    page: int = 1
    size: int = 20
    status: NotaStatus | None = None
    data_inicial: date | None = None
    data_final: date | None = None
    telefone: str | None = None
    chave: str | None = None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


@dataclass(frozen=True, slots=True)
class PaginatedOutput[T]:
    items: list[T]
    page: int
    size: int
    total: int
