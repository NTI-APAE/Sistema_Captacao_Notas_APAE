import logging
import sys

from playwright.sync_api import sync_playwright

import config
from api_client import ApiNotasClient
from automacao_notalegal import AutomacaoNotaLegal
from models import Nota


def obter_ou_criar_nota(chave: str | None, api: ApiNotasClient) -> Nota:
    if chave:
        chave = "".join(ch for ch in chave if ch.isdigit())
        if len(chave) != 44:
            raise SystemExit("Chave invalida.")
        api.importar_chaves(
            caminho_arquivo="teste_direto",
            chaves=[chave],
            total_linhas=1,
            total_invalidas=0,
            total_duplicadas_txt=0,
        )

    nota = api.obter_proxima_nota()
    if not nota:
        raise SystemExit("Nao ha notas pendentes na fila central da API.")
    return nota


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    chave = sys.argv[1] if len(sys.argv) > 1 else None
    api = ApiNotasClient()
    nota = obter_ou_criar_nota(chave, api)

    automacao = AutomacaoNotaLegal(
        log_callback=print,
        api_client=api,
    )
    automacao._pause_event.set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=150)
        page = browser.new_page()
        page.set_default_timeout(config.TIMEOUT_PADRAO_MS)
        page.goto(config.URL_LOGIN or "about:blank")

        print("\nFaca login manualmente e deixe o portal pronto.")
        print("Quando estiver na tela depois do login, pressione Enter aqui para testar uma nota.")
        input()

        automacao._processar_nota(page, nota)
        nota_atualizada = api.obter_nota(nota.id)
        print("\nResultado:")
        if nota_atualizada:
            print(f"ID: {nota_atualizada.id}")
            print(f"Chave: {nota_atualizada.chave}")
            print(f"Status: {nota_atualizada.status}")
            print(f"Mensagem: {nota_atualizada.mensagem}")

        input("\nPressione Enter para fechar o navegador de teste...")
        browser.close()


if __name__ == "__main__":
    main()
