from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.domain.entities.execucao_cadastro import ExecucaoCadastro
from app.domain.enums.execucao_fase import ExecucaoFase
from app.domain.enums.execucao_status import ExecucaoStatus


@dataclass(frozen=True, slots=True)
class ExecucaoCadastroOutput:
    id: UUID
    nota_fiscal_id: UUID
    tentativa: int
    status: ExecucaoStatus
    mensagem: str | None
    valor_obtido: Decimal | None
    data_emissao_obtida: date | None
    tempo_segundos: Decimal | None
    iniciado_em: datetime | None
    finalizado_em: datetime | None
    criado_em: datetime
    worker_id: str | None
    ultimo_heartbeat_em: datetime | None
    lease_expira_em: datetime | None
    fase_portal: ExecucaoFase
    motivo_recuperacao: str | None

    @classmethod
    def from_domain(cls, execucao: ExecucaoCadastro) -> "ExecucaoCadastroOutput":
        return cls(
            id=execucao.id,
            nota_fiscal_id=execucao.nota_fiscal_id,
            tentativa=execucao.tentativa,
            status=execucao.status,
            mensagem=execucao.mensagem,
            valor_obtido=execucao.valor_obtido,
            data_emissao_obtida=execucao.data_emissao_obtida,
            tempo_segundos=execucao.tempo_segundos,
            iniciado_em=execucao.iniciado_em,
            finalizado_em=execucao.finalizado_em,
            criado_em=execucao.criado_em,
            worker_id=execucao.worker_id,
            ultimo_heartbeat_em=execucao.ultimo_heartbeat_em,
            lease_expira_em=execucao.lease_expira_em,
            fase_portal=execucao.fase_portal,
            motivo_recuperacao=execucao.motivo_recuperacao,
        )
