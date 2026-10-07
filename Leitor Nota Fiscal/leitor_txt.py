import re
from pathlib import Path

from models import ProcessamentoTXT


TAMANHO_CHAVE_NOTA = 44
PADRAO_CHAVE_DIRETA = re.compile(rf"^\d{{{TAMANHO_CHAVE_NOTA}}}$")
PADROES_QRCODE = (
    re.compile(r"p\s*=\s*(.*?)(?=[\]}])", re.IGNORECASE | re.DOTALL),
    re.compile(r"nfce\.s[^\d\]}]*(\d.*?)(?=[\]}])", re.IGNORECASE | re.DOTALL),
)
PADRAO_INICIO_QRCODE = re.compile(r"p\s*=|nfce\.s", re.IGNORECASE)
PADRAO_DELIMITADOR_QRCODE = re.compile(r"[\]}]")


def _somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _candidato_qrcode_valido(candidato: str) -> str | None:
    chave = _somente_digitos(candidato)
    if len(chave) != TAMANHO_CHAVE_NOTA:
        return None
    return chave


def extrair_chaves(texto: str) -> list[str]:
    """
    Extrai uma ou mais chaves/codigos de um trecho de texto.

    Formatos aceitos:
    - QR Code com "p=" e separador "}" ou "]".
    - QR Code quebrado/truncado começando em "nfce.s..." e separador "}" ou "]".
    - Chave digitada manualmente em uma linha somente numerica.
    - Chaves quebradas por quebra de linha ou coladas no mesmo trecho.
    """
    texto = texto.strip()
    if not texto:
        return []

    candidatos: list[tuple[int, int, str]] = []
    trechos_vistos: set[tuple[int, int, str]] = set()

    for padrao in PADROES_QRCODE:
        for match in padrao.finditer(texto):
            chave = _candidato_qrcode_valido(match.group(1))
            trecho = (*match.span(1), chave or "")
            if chave and trecho not in trechos_vistos:
                trechos_vistos.add(trecho)
                candidatos.append((*match.span(1), chave))

    inicio_linha = 0
    for linha_com_quebra in texto.splitlines(keepends=True):
        linha = linha_com_quebra.strip()
        inicio_conteudo = inicio_linha + len(linha_com_quebra) - len(linha_com_quebra.lstrip())
        fim_conteudo = inicio_conteudo + len(linha)
        linha = linha.strip()
        if PADRAO_CHAVE_DIRETA.fullmatch(linha):
            candidatos.append((inicio_conteudo, fim_conteudo, linha))
        inicio_linha += len(linha_com_quebra)

    candidatos.sort(key=lambda item: (item[0], item[1]))
    return [chave for _, _, chave in candidatos]


def extrair_chave(linha: str) -> str | None:
    """
    Mantem compatibilidade com o fluxo antigo, retornando a primeira chave.
    """
    chaves = extrair_chaves(linha)
    return chaves[0] if chaves else None


def _contar_linhas_invalidas(linhas: list[str]) -> int:
    total_invalidas = 0
    aguardando_continuacao = False

    for linha in linhas:
        if extrair_chaves(linha):
            aguardando_continuacao = False
            continue

        tem_inicio = bool(PADRAO_INICIO_QRCODE.search(linha))
        tem_fim = bool(PADRAO_DELIMITADOR_QRCODE.search(linha))

        if aguardando_continuacao:
            if tem_fim:
                aguardando_continuacao = False
            continue

        if tem_inicio and not tem_fim:
            aguardando_continuacao = True
            continue

        total_invalidas += 1

    if aguardando_continuacao:
        total_invalidas += 1

    return total_invalidas


def processar_arquivo_txt(caminho_arquivo: str | Path) -> ProcessamentoTXT:
    caminho = Path(caminho_arquivo)
    chaves: list[str] = []
    vistas: set[str] = set()
    total_duplicadas = 0

    conteudo = caminho.read_text(encoding="utf-8", errors="ignore")
    linhas = [linha.strip() for linha in conteudo.splitlines() if linha.strip()]
    total_linhas = len(linhas)
    total_invalidas = _contar_linhas_invalidas(linhas)

    for chave in extrair_chaves(conteudo):
        if chave in vistas:
            total_duplicadas += 1
            continue

        vistas.add(chave)
        chaves.append(chave)

    return ProcessamentoTXT(
        caminho_arquivo=str(caminho),
        total_linhas=total_linhas,
        total_validas=len(chaves),
        total_invalidas=total_invalidas,
        total_duplicadas=total_duplicadas,
        chaves=chaves,
    )
