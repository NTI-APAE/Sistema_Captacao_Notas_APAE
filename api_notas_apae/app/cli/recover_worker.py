import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.domain.enums.execucao_status import ExecucaoStatus
from app.infrastructure.config import get_settings
from app.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.execucao_cadastro_input import RegistrarResultadoCadastroInput
from app.services.execucoes import RegistrarResultadoCadastroService
from app.services.worker import (
    ListarExecucoesReconciliacaoService,
    RecuperarExecucoesExpiradasService,
)

FINAL_STATUSES = (
    ExecucaoStatus.SUCESSO,
    ExecucaoStatus.DUPLICADA,
    ExecucaoStatus.IGNORADA,
    ExecucaoStatus.ERRO,
)


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, ExecucaoStatus):
        return value.value
    raise TypeError(f"Tipo nao serializavel: {type(value).__name__}")


def _output_dict(output) -> dict:
    return {
        "execucao_id": output.id,
        "nota_fiscal_id": output.nota_fiscal_id,
        "tentativa": output.tentativa,
        "status": output.status,
        "mensagem": output.mensagem,
        "fase_portal": output.fase_portal.value,
        "worker_id": output.worker_id,
        "lease_expira_em": output.lease_expira_em,
        "motivo_recuperacao": output.motivo_recuperacao,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recupera e reconcilia execucoes de cadastro abandonadas",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "recover",
        help="marca reservas abandonadas como reprocessaveis e isola efeitos incertos",
    )
    subparsers.add_parser(
        "list",
        help="lista execucoes cujo resultado externo precisa de reconciliacao",
    )

    reconcile = subparsers.add_parser(
        "reconcile",
        help="registra o resultado confirmado de uma execucao isolada",
    )
    reconcile.add_argument("--execucao-id", required=True, type=UUID)
    reconcile.add_argument(
        "--status",
        required=True,
        choices=[status.value for status in FINAL_STATUSES],
    )
    reconcile.add_argument("--mensagem")
    reconcile.add_argument("--valor", type=Decimal)
    reconcile.add_argument("--data-emissao", type=date.fromisoformat)
    reconcile.add_argument("--tempo-segundos", type=Decimal)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    settings = get_settings()

    if args.command == "recover":
        outputs = RecuperarExecucoesExpiradasService(
            SQLAlchemyUnitOfWork(),
            timeout_minutes=settings.worker_execution_timeout_minutes,
        ).execute()
        print(
            json.dumps(
                {"recuperadas": [_output_dict(output) for output in outputs]},
                default=_json_default,
                ensure_ascii=False,
            )
        )
        return

    if args.command == "list":
        outputs = ListarExecucoesReconciliacaoService(SQLAlchemyUnitOfWork()).execute()
        print(
            json.dumps(
                {"pendentes": [_output_dict(output) for output in outputs]},
                default=_json_default,
                ensure_ascii=False,
            )
        )
        return

    output = RegistrarResultadoCadastroService(SQLAlchemyUnitOfWork()).execute(
        RegistrarResultadoCadastroInput(
            execucao_id=args.execucao_id,
            status=ExecucaoStatus(args.status),
            mensagem=args.mensagem,
            valor=args.valor,
            data_emissao=args.data_emissao,
            tempo_segundos=args.tempo_segundos,
        )
    )
    print(json.dumps(_output_dict(output), default=_json_default, ensure_ascii=False))


if __name__ == "__main__":
    main()
