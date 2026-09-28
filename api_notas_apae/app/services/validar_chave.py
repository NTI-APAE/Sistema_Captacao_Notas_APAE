import re
from urllib.parse import parse_qs, urlparse


def validar_chave_acesso(chave: str) -> bool:
    """
    Valida o formato e o dígito verificador de uma
    chave de acesso de documento fiscal com 44 dígitos.

    Isso não comprova que a nota existe ou foi autorizada.
    """
    if not re.fullmatch(r"[0-9]{44}", chave):
        return False

    soma = 0
    peso = 2

    for digito in reversed(chave[:43]):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1

    resto = soma % 11
    digito_verificador = 0 if resto < 2 else 11 - resto

    return digito_verificador == int(chave[43])


def extrair_chave_acesso(conteudo: str) -> str | None:
    """
    Procura uma chave de 44 dígitos no conteúdo do QR Code.

    Suporta, entre outros casos, o parâmetro 'chNFe'
    e conteúdos que começam com a chave seguida de '|'.
    """
    conteudo = conteudo.strip()

    # Caso 1: URL com parâmetro chNFe.
    try:
        parametros = parse_qs(urlparse(conteudo).query)

        for nome, valores in parametros.items():
            if nome.lower() == "chnfe":
                for valor in valores:
                    if validar_chave_acesso(valor):
                        return valor
    except ValueError:
        pass

    # Caso 2: chave no início do conteúdo.
    candidato = conteudo.split("|", 1)[0]

    if validar_chave_acesso(candidato):
        return candidato

    # Caso 3: chave de 44 dígitos dentro do conteúdo.
    for candidato in re.findall(r"(?<!\d)[0-9]{44}(?!\d)", conteudo):
        if validar_chave_acesso(candidato):
            return candidato

    return None
