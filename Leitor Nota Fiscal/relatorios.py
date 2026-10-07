from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment

from api_client import ApiNotasClient
from models import STATUS_ERRO, STATUS_IGNORADA


STATUS_RELATORIO_MANUAL = (STATUS_IGNORADA, STATUS_ERRO)


def _formatar_data_br(valor: object) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    try:
        ano, mes, dia = texto[:10].split("-")
        return f"{dia}/{mes}/{ano}"
    except ValueError:
        return texto


def _formatar_data_hora_br(valor: object) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    normalizado = texto.replace("T", " ")
    partes = normalizado.split(" ", 1)
    data_br = _formatar_data_br(partes[0])
    if len(partes) == 1:
        return data_br
    hora = partes[1].split(".")[0].strip()
    return f"{data_br} {hora}" if hora else data_br


def gerar_resumo_por_dia(data_inicial: str, data_final: str) -> list[dict[str, object]]:
    linhas = ApiNotasClient().relatorio_por_dia(data_inicial, data_final)
    return [
        {
            "data": _formatar_data_br(linha.data),
            "cadastradas": linha.cadastradas,
            "valor_cadastradas": linha.valor_cadastradas,
            "tempo_total_segundos": linha.tempo_total_segundos,
            "fora_prazo": linha.fora_prazo,
            "valor_fora_prazo": linha.valor_fora_prazo,
            "duplicadas": linha.duplicadas,
            "erros": linha.erros,
            "valor_erros": linha.valor_erros,
            "ignoradas": linha.ignoradas,
            "pendentes": linha.pendentes,
            "total": linha.total,
        }
        for linha in linhas
    ]


def gerar_detalhamento(data_inicial: str, data_final: str) -> list[dict[str, object]]:
    linhas = ApiNotasClient().detalhamento_relatorio(
        data_inicial, data_final, STATUS_RELATORIO_MANUAL
    )
    for linha in linhas:
        linha["codigo_nota_fiscal"] = linha.get("chave", "")
        linha["data_emissao_nota"] = _formatar_data_br(linha.get("data_emissao_nota"))
        linha["data_importacao"] = _formatar_data_hora_br(linha.get("data_importacao"))
        linha["data_cadastro"] = _formatar_data_hora_br(linha.get("data_cadastro"))
    return linhas


def exportar_relatorio_excel(
    caminho_saida: str | Path,
    data_inicial: str,
    data_final: str,
) -> Path:
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    resumo = gerar_resumo_por_dia(data_inicial, data_final)
    detalhamento = gerar_detalhamento(data_inicial, data_final)

    resumo_df = pd.DataFrame(
        resumo,
        columns=[
            "data",
            "cadastradas",
            "valor_cadastradas",
            "tempo_total_segundos",
            "fora_prazo",
            "valor_fora_prazo",
            "duplicadas",
            "erros",
            "valor_erros",
            "ignoradas",
            "pendentes",
            "total",
        ],
    )
    detalhamento_df = pd.DataFrame(
        detalhamento,
        columns=[
            "codigo_nota_fiscal",
            "valor",
            "data_emissao_nota",
            "tempo_cadastro_segundos",
            "status",
            "mensagem",
            "arquivo_origem",
            "data_importacao",
            "data_cadastro",
            "tentativa",
        ],
    )

    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        resumo_df.to_excel(writer, index=False, sheet_name="Resumo por dia")
        detalhamento_df.to_excel(writer, index=False, sheet_name="Detalhamento")

        for sheet_name in ("Resumo por dia", "Detalhamento"):
            worksheet = writer.sheets[sheet_name]
            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(
                    max(max_length + 2, 12),
                    60,
                )
            for row in worksheet.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")

    return caminho
