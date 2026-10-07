from uuid import UUID

from sqlalchemy import select

from app.domain.entities.resumo_operacao_leitor import ResumoOperacaoLeitor
from app.models.resumo_operacao_leitor_model import ResumoOperacaoLeitorModel


class SQLAlchemyResumoOperacaoLeitorRepository:
    def __init__(self, session) -> None:
        self.session = session

    def buscar_por_operacao_id(self, operacao_id: UUID) -> ResumoOperacaoLeitor | None:
        model = self.session.scalar(
            select(ResumoOperacaoLeitorModel).where(
                ResumoOperacaoLeitorModel.operacao_id == operacao_id
            )
        )
        return self._to_domain(model) if model else None

    def adicionar(self, resumo: ResumoOperacaoLeitor) -> None:
        self.session.add(
            ResumoOperacaoLeitorModel(
                id=resumo.id,
                operacao_id=resumo.operacao_id,
                total_notas=resumo.total_notas,
                tentadas=resumo.tentadas,
                cadastradas=resumo.cadastradas,
                duplicadas=resumo.duplicadas,
                ignoradas=resumo.ignoradas,
                erros=resumo.erros,
                valor_total=resumo.valor_total,
                valor_cadastradas=resumo.valor_cadastradas,
                valor_duplicadas=resumo.valor_duplicadas,
                valor_ignoradas=resumo.valor_ignoradas,
                valor_erros=resumo.valor_erros,
                tempo_total_segundos=resumo.tempo_total_segundos,
                tempo_notas_segundos=resumo.tempo_notas_segundos,
            )
        )

    @staticmethod
    def _to_domain(model: ResumoOperacaoLeitorModel) -> ResumoOperacaoLeitor:
        return ResumoOperacaoLeitor(
            id=model.id,
            operacao_id=model.operacao_id,
            total_notas=model.total_notas,
            tentadas=model.tentadas,
            cadastradas=model.cadastradas,
            duplicadas=model.duplicadas,
            ignoradas=model.ignoradas,
            erros=model.erros,
            valor_total=model.valor_total,
            valor_cadastradas=model.valor_cadastradas,
            valor_duplicadas=model.valor_duplicadas,
            valor_ignoradas=model.valor_ignoradas,
            valor_erros=model.valor_erros,
            tempo_total_segundos=model.tempo_total_segundos,
            tempo_notas_segundos=model.tempo_notas_segundos,
            criado_em=model.criado_em,
        )
