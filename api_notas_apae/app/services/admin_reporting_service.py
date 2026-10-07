from datetime import datetime, timedelta

from app.infrastructure.config import get_settings
from app.models.nota_fiscal_model import NotaFiscalModel
from app.models.submissao_nota_model import SubmissaoNotaModel
from app.schemas.admin_reporting_filters import TIMEZONE, AdminReportingFilter


class AdminReportingService:
    """Leitura operacional sem modificar status, notas ou consentimentos."""

    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _delay(start, end):
        if start is None or end is None:
            return None
        return max(0, int((end - start).total_seconds()))

    @classmethod
    def _decorate_message(cls, item):
        item["atraso_processamento_segundos"] = cls._delay(
            item.get("timestamp"), item.get("processed_at")
        )
        return item

    @classmethod
    def _decorate_note(cls, item):
        item["atraso_processamento_segundos"] = cls._delay(
            item.get("whatsapp_timestamp"), item.get("whatsapp_processed_at")
        )
        item["historico_mensagens"] = [
            cls._decorate_message(message)
            for message in item.get("historico_mensagens", [])
        ]
        return item

    @classmethod
    def _decorate_page(cls, page):
        page["items"] = [cls._decorate_note(item) for item in page["items"]]
        return page

    def resumo(self, hoje=None):
        hoje = hoje or datetime.now(TIMEZONE).date()
        inicio = hoje - timedelta(days=29)
        recebimentos = self.repository.recebimentos_por_dia(inicio, hoje)
        recebimentos = {str(key): value for key, value in recebimentos.items()}
        series = [
            {
                "dia": inicio + timedelta(days=i),
                "total": recebimentos.get(str(inicio + timedelta(days=i)), 0),
            }
            for i in range(30)
        ]
        return {
            "indicadores": self.repository.indicadores(
                hoje,
                prazo_maximo_emissao_meses=get_settings().prazo_maximo_emissao_meses,
            ),
            "series": series,
            "maximo": max(1, max(item["total"] for item in series)),
            "status_submissoes": self.repository.por_status(SubmissaoNotaModel),
            "status_notas": self.repository.por_status(NotaFiscalModel),
            "leitor": self.repository.resumo_leitor(),
            "result": self.notas(AdminReportingFilter(size=8)),
        }

    def leitor(self, filtro):
        return self.repository.resumo_leitor(filtro)

    def notas(self, filtro, pessoa_id=None):
        return self._decorate_page(self.repository.notas(filtro, pessoa_id))

    def nota(self, nota_id):
        item = self.repository.nota(nota_id, AdminReportingFilter())
        return self._decorate_note(item) if item else None

    def contatos(self, filtro):
        return self.repository.contatos(filtro)

    def contato(self, pessoa_id, filtro):
        contato = self.repository.contato(pessoa_id)
        if contato is None:
            return None
        return {
            "contato": contato,
            "result": self.notas(filtro, pessoa_id),
            "consentimentos": self.repository.consentimentos(
                pessoa_id, filtro.model_copy(update={"page": filtro.consent_page})
            ),
        }
