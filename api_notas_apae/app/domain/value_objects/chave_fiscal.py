from dataclasses import dataclass

from app.domain.exceptions.chave_invalida_exception import ChaveInvalidaException


@dataclass(frozen=True, slots=True)
class ChaveFiscal:
    valor: str

    def __post_init__(self) -> None:
        if not isinstance(self.valor, str):
            raise ChaveInvalidaException(str(self.valor))

        valor_normalizado = self.valor.strip()
        if len(valor_normalizado) != 44 or not valor_normalizado.isdigit():
            raise ChaveInvalidaException(valor_normalizado)

        object.__setattr__(self, "valor", valor_normalizado)

    def __str__(self) -> str:
        return self.valor
