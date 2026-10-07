from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.time import utc_now


@dataclass(slots=True)
class ResumoOperacaoLeitor:
    operacao_id: UUID
    total_notas: int
    tentadas: int
    cadastradas: int
    duplicadas: int
    ignoradas: int
    erros: int
    valor_total: Decimal
    valor_cadastradas: Decimal
    valor_duplicadas: Decimal
    valor_ignoradas: Decimal
    valor_erros: Decimal
    tempo_total_segundos: Decimal
    tempo_notas_segundos: Decimal
    id: UUID = field(default_factory=uuid4)
    criado_em: datetime = field(default_factory=utc_now)

    def mesmos_dados(self, outro: "ResumoOperacaoLeitor") -> bool:
        return (
            self.operacao_id == outro.operacao_id
            and self.total_notas == outro.total_notas
            and self.tentadas == outro.tentadas
            and self.cadastradas == outro.cadastradas
            and self.duplicadas == outro.duplicadas
            and self.ignoradas == outro.ignoradas
            and self.erros == outro.erros
            and self.valor_total == outro.valor_total
            and self.valor_cadastradas == outro.valor_cadastradas
            and self.valor_duplicadas == outro.valor_duplicadas
            and self.valor_ignoradas == outro.valor_ignoradas
            and self.valor_erros == outro.valor_erros
            and self.tempo_total_segundos == outro.tempo_total_segundos
            and self.tempo_notas_segundos == outro.tempo_notas_segundos
        )
