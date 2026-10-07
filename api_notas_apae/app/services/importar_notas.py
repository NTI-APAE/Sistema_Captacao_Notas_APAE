import logging

from app.domain.entities.nota_fiscal import NotaFiscal
from app.domain.enums.nota_status import NotaStatus
from app.domain.exceptions.chave_invalida_exception import ChaveInvalidaException
from app.domain.services.chave_fiscal_service import ChaveFiscalService
from app.repositories.contracts import Transaction
from app.repositories.exceptions import DuplicateKeyError
from app.schemas.importar_notas_output import ImportarNotasOutput
from app.schemas.importar_notas_service_input import ImportarNotasInput


class ImportarNotasTxtService:
    """Importa chaves vindas do leitor sem criar pessoa/telefone artificial."""

    def __init__(self, unit_of_work: Transaction) -> None:
        self._unit_of_work = unit_of_work
        self._chave_service = ChaveFiscalService()

    def execute(self, data: ImportarNotasInput) -> ImportarNotasOutput:
        chaves_validas: list[str] = []
        invalidas_api = 0
        vistas: set[str] = set()
        for chave in data.chaves:
            try:
                normalizada = self._chave_service.normalizar_e_validar(chave)
            except ChaveInvalidaException:
                invalidas_api += 1
                continue
            if normalizada in vistas:
                continue
            vistas.add(normalizada)
            chaves_validas.append(normalizada)

        for tentativa in range(3):
            try:
                return self._persistir(data, chaves_validas, invalidas_api)
            except DuplicateKeyError:
                if tentativa == 2:
                    raise
                logging.getLogger(__name__).warning(
                    "Conflito concorrente ao importar notas; repetindo lote"
                )
        raise AssertionError("fluxo de importação inesperado")

    def _persistir(
        self,
        data: ImportarNotasInput,
        chaves: list[str],
        invalidas_api: int,
    ) -> ImportarNotasOutput:
        inseridas = 0
        reativadas = 0
        ja_existentes = 0
        with self._unit_of_work as uow:
            for chave in chaves:
                nota = uow.notas.buscar_por_chave(chave)
                if nota is None:
                    uow.notas.adicionar(NotaFiscal(chave=chave))
                    inseridas += 1
                    continue
                if nota.status in {
                    NotaStatus.ERRO_CADASTRO,
                    NotaStatus.IGNORADA,
                    NotaStatus.PAUSADA,
                }:
                    nota.reprocessar()
                    uow.notas.salvar(nota)
                    reativadas += 1
                    continue
                ja_existentes += 1
            uow.commit()

        return ImportarNotasOutput(
            total_linhas=data.total_linhas,
            total_validas=len(chaves),
            total_invalidas=data.total_invalidas + invalidas_api,
            total_duplicadas=data.total_duplicadas_txt + ja_existentes,
            total_inseridas=inseridas,
            total_reativadas=reativadas,
            total_ja_existentes=ja_existentes,
        )
