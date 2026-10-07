from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import psycopg
from psycopg.rows import dict_row

from config import DATABASE_PATH, DATABASE_URL, PRAZO_MAXIMO_EMISSAO_MESES
from models import (
    Nota,
    RelatorioDia,
    ResultadoImportacao,
    STATUS_AGUARDANDO_CAPTCHA,
    STATUS_CADASTRADA,
    STATUS_DUPLICADA,
    STATUS_ERRO,
    STATUS_IGNORADA,
    STATUS_PAUSADA,
    STATUS_PENDENTE,
    STATUS_PROCESSANDO,
    agora_iso,
)


def _subtrair_meses(data_base: date, meses: int) -> date:
    mes = data_base.month - max(0, meses)
    ano = data_base.year
    while mes <= 0:
        mes += 12
        ano -= 1
    if mes == 12:
        primeiro_proximo_mes = date(ano + 1, 1, 1)
    else:
        primeiro_proximo_mes = date(ano, mes + 1, 1)
    dias_no_mes = (primeiro_proximo_mes - date(ano, mes, 1)).days
    return date(ano, mes, min(data_base.day, dias_no_mes))


def data_limite_fora_prazo() -> date:
    return _subtrair_meses(date.today(), PRAZO_MAXIMO_EMISSAO_MESES)


def conectar(db_path: Path | str = DATABASE_PATH) -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def inicializar_banco(db_path: Path | str = DATABASE_PATH) -> None:
    with conectar(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notas (
                id SERIAL PRIMARY KEY,
                chave TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                mensagem TEXT DEFAULT '',
                valor REAL,
                data_emissao_nota TEXT,
                arquivo_origem TEXT DEFAULT '',
                data_importacao TEXT,
                data_cadastro TEXT,
                tempo_cadastro_segundos REAL,
                tentativa INTEGER NOT NULL DEFAULT 0,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS arquivos_importados (
                id SERIAL PRIMARY KEY,
                nome_arquivo TEXT NOT NULL,
                caminho_arquivo TEXT NOT NULL,
                total_linhas INTEGER NOT NULL DEFAULT 0,
                total_validas INTEGER NOT NULL DEFAULT 0,
                total_invalidas INTEGER NOT NULL DEFAULT 0,
                total_duplicadas INTEGER NOT NULL DEFAULT 0,
                data_importacao TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notas_status ON notas(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notas_data_cadastro ON notas(data_cadastro)")
        _garantir_coluna(conn, "notas", "valor", "REAL")
        _garantir_coluna(conn, "notas", "data_emissao_nota", "TEXT")
        _garantir_coluna(conn, "notas", "tempo_cadastro_segundos", "REAL")


def _garantir_coluna(conn: psycopg.Connection, tabela: str, coluna: str, definicao: str) -> None:
    row = conn.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
          AND column_name = %s
        """,
        (tabela, coluna),
    ).fetchone()
    if not row:
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def _nota_from_row(row: dict[str, object]) -> Nota:
    return Nota(
        id=row["id"],
        chave=row["chave"],
        status=row["status"],
        mensagem=row["mensagem"] or "",
        arquivo_origem=row["arquivo_origem"] or "",
        data_importacao=row["data_importacao"],
        data_cadastro=row["data_cadastro"],
        tentativa=row["tentativa"] or 0,
        criado_em=row["criado_em"],
        atualizado_em=row["atualizado_em"],
        valor=row["valor"],
        tempo_cadastro_segundos=row["tempo_cadastro_segundos"],
        data_emissao_nota=row["data_emissao_nota"],
    )


def importar_chaves(
    *,
    caminho_arquivo: Path | str,
    chaves: Iterable[str],
    total_linhas: int,
    total_invalidas: int,
    total_duplicadas_txt: int,
    db_path: Path | str = DATABASE_PATH,
) -> ResultadoImportacao:
    caminho = Path(caminho_arquivo)
    chaves_unicas = list(dict.fromkeys(chaves))
    data_importacao = agora_iso()
    inseridas = 0
    reativadas = 0
    ja_existentes = 0

    with conectar(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO arquivos_importados (
                nome_arquivo, caminho_arquivo, total_linhas, total_validas,
                total_invalidas, total_duplicadas, data_importacao
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                caminho.name,
                str(caminho),
                total_linhas,
                len(chaves_unicas),
                total_invalidas,
                total_duplicadas_txt,
                data_importacao,
            ),
        ).fetchone()
        arquivo_id = int(row["id"])

        for chave in chaves_unicas:
            existe = conn.execute("SELECT id, status FROM notas WHERE chave = %s", (chave,)).fetchone()
            if existe:
                if existe["status"] in {STATUS_ERRO, STATUS_IGNORADA}:
                    conn.execute(
                        """
                        UPDATE notas
                        SET status = %s,
                            mensagem = %s,
                            arquivo_origem = %s,
                            data_importacao = %s,
                            data_cadastro = NULL,
                            tentativa = 0,
                            valor = NULL,
                            data_emissao_nota = NULL,
                            tempo_cadastro_segundos = NULL,
                            atualizado_em = %s
                        WHERE id = %s
                        """,
                        (
                            STATUS_PENDENTE,
                            "Reimportada para novo envio",
                            caminho.name,
                            data_importacao,
                            data_importacao,
                            existe["id"],
                        ),
                    )
                    reativadas += 1
                    continue
                ja_existentes += 1
                continue
            conn.execute(
                """
                INSERT INTO notas (
                    chave, status, mensagem, arquivo_origem, data_importacao,
                    data_cadastro, tentativa, criado_em, atualizado_em
                )
                VALUES (%s, %s, %s, %s, %s, NULL, 0, %s, %s)
                """,
                (
                    chave,
                    STATUS_PENDENTE,
                    "Importada e aguardando cadastro",
                    caminho.name,
                    data_importacao,
                    data_importacao,
                    data_importacao,
                ),
            )
            inseridas += 1

        total_duplicadas = total_duplicadas_txt + ja_existentes
        conn.execute(
            "UPDATE arquivos_importados SET total_duplicadas = %s WHERE id = %s",
            (total_duplicadas, arquivo_id),
        )

    return ResultadoImportacao(
        arquivo_id=arquivo_id,
        total_linhas=total_linhas,
        total_validas=len(chaves_unicas),
        total_invalidas=total_invalidas,
        total_duplicadas=total_duplicadas,
        total_inseridas=inseridas,
        total_reativadas=reativadas,
        total_ja_existentes=ja_existentes,
    )


def listar_notas(db_path: Path | str = DATABASE_PATH, limite: Optional[int] = None) -> list[Nota]:
    sql = "SELECT * FROM notas ORDER BY id DESC"
    params: tuple[object, ...] = ()
    if limite:
        sql += " LIMIT %s"
        params = (limite,)
    with conectar(db_path) as conn:
        return [_nota_from_row(row) for row in conn.execute(sql, params).fetchall()]


def listar_notas_adicionadas_em(
    data_importacao: str,
    db_path: Path | str = DATABASE_PATH,
    limite: Optional[int] = None,
) -> list[Nota]:
    sql = """
        SELECT * FROM notas
        WHERE CAST(data_importacao AS date) = CAST(%s AS date)
        ORDER BY id DESC
    """
    params: list[object] = [data_importacao]
    if limite:
        sql += " LIMIT %s"
        params.append(limite)
    with conectar(db_path) as conn:
        return [_nota_from_row(row) for row in conn.execute(sql, tuple(params)).fetchall()]


def listar_notas_operacao(
    data_referencia: str,
    db_path: Path | str = DATABASE_PATH,
    *,
    max_tentativas: Optional[int] = None,
    limite: Optional[int] = None,
) -> list[Nota]:
    params: list[object] = [
        data_referencia,
        STATUS_PENDENTE,
        STATUS_ERRO,
        STATUS_AGUARDANDO_CAPTCHA,
        STATUS_PAUSADA,
        STATUS_PROCESSANDO,
    ]
    filtro_tentativas = ""
    if max_tentativas is not None:
        filtro_tentativas = "AND (status <> %s OR tentativa < %s)"
        params.extend([STATUS_ERRO, max_tentativas])

    sql = f"""
        SELECT * FROM notas
        WHERE CAST(data_importacao AS date) = CAST(%s AS date)
           OR (
                status IN (%s, %s, %s, %s, %s)
                {filtro_tentativas}
           )
        ORDER BY
            CASE
                WHEN status = %s THEN 0
                WHEN status = %s THEN 1
                WHEN status = %s THEN 2
                WHEN status = %s THEN 3
                WHEN status = %s THEN 4
                ELSE 5
            END,
            tentativa ASC,
            COALESCE(data_importacao, criado_em) ASC,
            id ASC
    """
    params.extend([STATUS_PENDENTE, STATUS_ERRO, STATUS_AGUARDANDO_CAPTCHA, STATUS_PAUSADA, STATUS_PROCESSANDO])
    if limite:
        sql += " LIMIT %s"
        params.append(limite)

    with conectar(db_path) as conn:
        return [_nota_from_row(row) for row in conn.execute(sql, tuple(params)).fetchall()]


def obter_nota(nota_id: int, db_path: Path | str = DATABASE_PATH) -> Optional[Nota]:
    with conectar(db_path) as conn:
        row = conn.execute("SELECT * FROM notas WHERE id = %s", (nota_id,)).fetchone()
        return _nota_from_row(row) if row else None


def proxima_nota_para_processar(
    db_path: Path | str = DATABASE_PATH,
    *,
    max_tentativas: Optional[int] = None,
) -> Optional[Nota]:
    params: list[object] = [STATUS_PENDENTE, STATUS_ERRO]
    if max_tentativas is not None:
        filtro_tentativas = "AND tentativa < %s"
        params.append(max_tentativas)
    else:
        filtro_tentativas = ""

    agora = agora_iso()
    params.extend([STATUS_PROCESSANDO, "Reservada para processamento", agora])

    with conectar(db_path) as conn:
        row = conn.execute(
            f"""
            WITH proxima AS (
                SELECT id
                FROM notas
                WHERE status IN (%s, %s)
                {filtro_tentativas}
                ORDER BY
                    CASE WHEN tentativa = 0 THEN 0 ELSE 1 END,
                    tentativa ASC,
                    id ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE notas
            SET status = %s,
                mensagem = %s,
                atualizado_em = %s
            WHERE id = (SELECT id FROM proxima)
            RETURNING *
            """,
            tuple(params),
        ).fetchone()
        return _nota_from_row(row) if row else None


def atualizar_status_nota(
    nota_id: int,
    status: str,
    mensagem: str = "",
    *,
    incrementar_tentativa: bool = False,
    definir_data_cadastro: bool = False,
    valor: Optional[float] = None,
    data_emissao_nota: Optional[str] = None,
    tempo_cadastro_segundos: Optional[float] = None,
    db_path: Path | str = DATABASE_PATH,
) -> None:
    agora = agora_iso()
    with conectar(db_path) as conn:
        conn.execute(
            """
            UPDATE notas
            SET status = %s,
                mensagem = %s,
                valor = CASE WHEN %s THEN %s ELSE valor END,
                data_emissao_nota = CASE WHEN %s THEN %s ELSE data_emissao_nota END,
                tempo_cadastro_segundos = CASE WHEN %s THEN %s ELSE tempo_cadastro_segundos END,
                data_cadastro = CASE WHEN %s THEN %s ELSE data_cadastro END,
                tentativa = tentativa + %s,
                atualizado_em = %s
            WHERE id = %s
            """,
            (
                status,
                mensagem,
                valor is not None,
                valor,
                data_emissao_nota is not None,
                data_emissao_nota,
                tempo_cadastro_segundos is not None,
                tempo_cadastro_segundos,
                definir_data_cadastro,
                agora,
                1 if incrementar_tentativa else 0,
                agora,
                nota_id,
            ),
        )


def contagem_por_status(db_path: Path | str = DATABASE_PATH) -> dict[str, int]:
    with conectar(db_path) as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS total FROM notas GROUP BY status").fetchall()
    return {row["status"]: row["total"] for row in rows}


def contadores_operacao(
    db_path: Path | str = DATABASE_PATH,
    *,
    max_tentativas: Optional[int] = None,
) -> dict[str, int]:
    params_fila: list[object] = [
        STATUS_PENDENTE,
        STATUS_ERRO,
        STATUS_AGUARDANDO_CAPTCHA,
        STATUS_PAUSADA,
        STATUS_PROCESSANDO,
    ]
    filtro_tentativas = ""
    if max_tentativas is not None:
        filtro_tentativas = "AND (status <> %s OR tentativa < %s)"
        params_fila.extend([STATUS_ERRO, max_tentativas])

    hoje = date.today().isoformat()
    with conectar(db_path) as conn:
        fila = conn.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM notas
            WHERE status IN (%s, %s, %s, %s, %s)
              {filtro_tentativas}
            """,
            tuple(params_fila),
        ).fetchone()["total"] or 0
        cadastradas_hoje = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM notas
            WHERE status = %s
              AND CAST(COALESCE(data_cadastro, atualizado_em, criado_em) AS date) = CAST(%s AS date)
            """,
            (STATUS_CADASTRADA, hoje),
        ).fetchone()["total"] or 0
        cadastradas_total = conn.execute(
            "SELECT COUNT(*) AS total FROM notas WHERE status = %s",
            (STATUS_CADASTRADA,),
        ).fetchone()["total"] or 0

    return {
        "fila_pendente": int(fila),
        "cadastradas_hoje": int(cadastradas_hoje),
        "cadastradas_total": int(cadastradas_total),
    }


def excluir_fila_processamento(db_path: Path | str = DATABASE_PATH) -> int:
    with conectar(db_path) as conn:
        cursor = conn.execute(
            """
            DELETE FROM notas
            WHERE status IN (%s, %s, %s, %s, %s)
            """,
            (STATUS_PENDENTE, STATUS_ERRO, STATUS_AGUARDANDO_CAPTCHA, STATUS_PAUSADA, STATUS_PROCESSANDO),
        )
        return int(cursor.rowcount or 0)


def limpar_historico_relatorios(
    db_path: Path | str = DATABASE_PATH,
    *,
    max_tentativas: Optional[int] = None,
) -> int:
    params: list[object] = [
        STATUS_CADASTRADA,
        STATUS_DUPLICADA,
        STATUS_IGNORADA,
    ]
    filtro_erro_final = ""
    if max_tentativas is not None:
        filtro_erro_final = "OR (status = %s AND tentativa >= %s)"
        params.extend([STATUS_ERRO, max_tentativas])

    with conectar(db_path) as conn:
        cursor = conn.execute(
            f"""
            DELETE FROM notas
            WHERE status IN (%s, %s, %s)
               {filtro_erro_final}
            """,
            tuple(params),
        )
        conn.execute("DELETE FROM arquivos_importados")
        return int(cursor.rowcount or 0)


def relatorio_por_dia(
    data_inicial: str,
    data_final: str,
    db_path: Path | str = DATABASE_PATH,
) -> list[RelatorioDia]:
    limite_fora_prazo = data_limite_fora_prazo().isoformat()
    data_referencia = "CAST(COALESCE(data_cadastro, data_importacao, criado_em) AS date)"
    with conectar(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                {data_referencia} AS data,
                SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) AS cadastradas,
                SUM(CASE WHEN status = %s THEN COALESCE(valor, 0) ELSE 0 END) AS valor_cadastradas,
                SUM(CASE WHEN status = %s THEN COALESCE(tempo_cadastro_segundos, 0) ELSE 0 END) AS tempo_total_segundos,
                SUM(CASE WHEN data_emissao_nota IS NOT NULL AND CAST(data_emissao_nota AS date) <= CAST(%s AS date) THEN 1 ELSE 0 END) AS fora_prazo,
                SUM(CASE WHEN data_emissao_nota IS NOT NULL AND CAST(data_emissao_nota AS date) <= CAST(%s AS date) THEN COALESCE(valor, 0) ELSE 0 END) AS valor_fora_prazo,
                SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) AS duplicadas,
                SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) AS erros,
                SUM(CASE WHEN status IN (%s, %s, %s) THEN COALESCE(valor, 0) ELSE 0 END) AS valor_erros,
                SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) AS ignoradas,
                SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) AS pendentes,
                COUNT(*) AS total
            FROM notas
            WHERE {data_referencia} BETWEEN CAST(%s AS date) AND CAST(%s AS date)
            GROUP BY {data_referencia}
            ORDER BY data ASC
            """,
            (
                STATUS_CADASTRADA,
                STATUS_CADASTRADA,
                STATUS_CADASTRADA,
                limite_fora_prazo,
                limite_fora_prazo,
                STATUS_DUPLICADA,
                STATUS_ERRO,
                STATUS_DUPLICADA,
                STATUS_ERRO,
                STATUS_IGNORADA,
                STATUS_IGNORADA,
                STATUS_PENDENTE,
                data_inicial,
                data_final,
            ),
        ).fetchall()

    return [
        RelatorioDia(
            data=row["data"].isoformat() if hasattr(row["data"], "isoformat") else row["data"],
            cadastradas=row["cadastradas"] or 0,
            valor_cadastradas=row["valor_cadastradas"] or 0.0,
            tempo_total_segundos=row["tempo_total_segundos"] or 0.0,
            fora_prazo=row["fora_prazo"] or 0,
            valor_fora_prazo=row["valor_fora_prazo"] or 0.0,
            duplicadas=row["duplicadas"] or 0,
            erros=row["erros"] or 0,
            valor_erros=row["valor_erros"] or 0.0,
            ignoradas=row["ignoradas"] or 0,
            pendentes=row["pendentes"] or 0,
            total=row["total"] or 0,
        )
        for row in rows
    ]


def detalhamento_relatorio(
    data_inicial: str,
    data_final: str,
    db_path: Path | str = DATABASE_PATH,
    *,
    statuses: Optional[Iterable[str]] = None,
) -> list[dict[str, object]]:
    filtro_status = ""
    params: list[object] = [data_inicial, data_final]
    if statuses:
        lista_status = list(statuses)
        placeholders = ", ".join("%s" for _ in lista_status)
        filtro_status = f"AND status IN ({placeholders})"
        params.extend(lista_status)

    with conectar(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT chave, valor, data_emissao_nota, tempo_cadastro_segundos, status, mensagem,
                   arquivo_origem, data_importacao, data_cadastro, tentativa
            FROM notas
            WHERE CAST(COALESCE(data_cadastro, data_importacao, criado_em) AS date)
                  BETWEEN CAST(%s AS date) AND CAST(%s AS date)
                  {filtro_status}
            ORDER BY COALESCE(data_cadastro, data_importacao, criado_em), id
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]
