from datetime import datetime, timedelta

from app.models.nota_fiscal_model import NotaFiscalModel
from app.models.submissao_nota_model import SubmissaoNotaModel
from app.schemas.admin_reporting_filters import TIMEZONE, AdminReportingFilter


class AdminReportingService:
    """Leitura operacional sem modificar status, notas ou consentimentos."""

    def __init__(self, repository):
        self.repository = repository

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
            "indicadores": self.repository.indicadores(hoje),
            "series": series,
            "maximo": max(1, max(item["total"] for item in series)),
            "status_submissoes": self.repository.por_status(SubmissaoNotaModel),
            "status_notas": self.repository.por_status(NotaFiscalModel),
            "result": self.repository.notas(AdminReportingFilter(size=8)),
        }

    def notas(self, filtro, pessoa_id=None):
        return self.repository.notas(filtro, pessoa_id)

    def nota(self, nota_id):
        return self.repository.nota(nota_id, AdminReportingFilter())

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
