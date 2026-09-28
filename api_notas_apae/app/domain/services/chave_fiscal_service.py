from app.domain.value_objects.chave_fiscal import ChaveFiscal


class ChaveFiscalService:
    def validar(self, chave: str) -> None:
        ChaveFiscal(chave)

    def normalizar_e_validar(self, chave: str) -> str:
        return ChaveFiscal(chave).valor
