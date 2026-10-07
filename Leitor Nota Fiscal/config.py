"""
Configuracoes do sistema.

Os seletores abaixo foram preenchidos com base na tela do portal enviada. Eles
usam texto visivel e XPath para evitar depender de IDs gerados pelo JSF.

Importante: este sistema nao resolve, quebra, contorna ou evita CAPTCHA. Quando
SELETOR_CAPTCHA identificar um CAPTCHA ou validacao manual, a automacao pausa e
aguarda o usuario resolver manualmente no navegador visivel.
"""

import os
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = BASE_DIR

DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
APP_ICON_PATH = RESOURCE_DIR / "assets" / "app_icon.ico"
PLAYWRIGHT_BROWSERS_DIR = BASE_DIR / "ms-playwright"

if PLAYWRIGHT_BROWSERS_DIR.exists():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(PLAYWRIGHT_BROWSERS_DIR))


def _carregar_env_local() -> None:
    """Carrega o .env ao lado do leitor sem depender de python-dotenv."""
    caminho = BASE_DIR / ".env"
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        nome = nome.strip()
        valor = valor.strip().strip('"').strip("'")
        if nome:
            os.environ.setdefault(nome, valor)


_carregar_env_local()

DATABASE_PATH = DATA_DIR / "notas.db"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://notas_apae:notas_apae@localhost:5432/notas_apae",
)
LOG_FILE = LOG_DIR / "sistema.log"

# API central. O leitor não mantém uma fila própria: notas, execuções e
# resultados ficam no banco da API Notas APAE.
NOTAS_API_URL = os.getenv("NOTAS_API_URL", "http://127.0.0.1:8000").rstrip("/")
NOTAS_API_INTERNAL_KEY = os.getenv("NOTAS_API_INTERNAL_KEY", "")
NOTAS_API_WORKER_KEY = os.getenv("WORKER_API_KEY", os.getenv("NOTAS_API_WORKER_KEY", ""))
NOTAS_API_TIMEOUT_SEGUNDOS = float(os.getenv("NOTAS_API_TIMEOUT_SEGUNDOS", "30"))
USAR_CHROME_INSTALADO_FALLBACK = True
PLAYWRIGHT_CHANNEL = os.getenv("PLAYWRIGHT_CHANNEL", "chrome")

# URL inicial para login manual. Deixe vazio para abrir uma pagina em branco.
URL_LOGIN = "https://sistemas1.sefaz.ma.gov.br/portalnotalegal/jsp/login/login.jsf"

# Preenchimento assistido da tela de login.
# O sistema apenas preenche CPF/CNPJ, senha e perfil. O CAPTCHA e o clique no
# botao Acessar continuam sendo feitos manualmente pelo usuario.
PREENCHER_LOGIN_AUTOMATICO = True
LOGIN_CPF_CNPJ = os.getenv("NOTALEGAL_LOGIN_CPF_CNPJ", "")
LOGIN_SENHA = os.getenv("NOTALEGAL_LOGIN_SENHA", "")
LOGIN_PERFIL_TEXTO = os.getenv("NOTALEGAL_LOGIN_PERFIL", "Entidades Beneficentes")
ESPERA_ANTES_PREENCHER_LOGIN_MS = 3000
TIMEOUT_CAMPO_LOGIN_MS = 3000
LOGIN_PERFIL_ALIASES = [
    "Entidades Beneficientes",
    "Entidade Beneficente",
]

# Se o portal alterar o HTML, preencha estes seletores apos inspecionar a tela.
# Quando ficarem vazios, a automacao usa seletores por texto e fallbacks.
CAMPO_LOGIN_CPF_CNPJ = ""
CAMPO_LOGIN_SENHA = ""
RADIO_LOGIN_PERFIL = ""

# Seletor CSS, XPath ou seletor Playwright do menu/link "Cadastrar Notas".
MENU_CADASTRAR_NOTAS = "text=Cadastrar Notas"

# Campo "Tipo da Nota" observado no DOM do portal.
CAMPO_TIPO_NOTA = "select[name='form1:j_id45']"

# Texto visivel da opcao que deve ser selecionada em "Tipo da Nota".
TIPO_NOTA_TEXTO = "NFCE - NOTA FISCAL AO CONSUMIDOR ELETR\u00d4NICA"

# Campo onde a chave da nota sera digitada, observado no DOM do portal.
CAMPO_CHAVE = "input[name='form1:j_id49']"

# Botao que consulta a chave, se existir. Na tela enviada nao ha botao separado.
BOTAO_CONSULTAR = ""

# Botao final "Cadastrar". O id abaixo veio do HTML informado:
# <input id="form1:j_id97" ... value="Cadastrar" type="button">
BOTAO_SALVAR = "input[id='form1:j_id97']"

# Aciona o mesmo Ajax declarado no onclick do botao Cadastrar, mais rapido e
# assertivo que depender apenas do clique visual.
USAR_A4J_DIRETO_CADASTRAR = True
A4J_FORM_CADASTRAR = "form1"
A4J_BOTAO_CADASTRAR = "form1:j_id97"

# Fallbacks para o botao Cadastrar caso o portal altere o id gerado pelo JSF.
BOTAO_SALVAR_FALLBACKS = [
    "input.botao_sistema[value='Cadastrar']",
    "xpath=//input[normalize-space(@value)='Cadastrar' and @type='button']",
    "xpath=//button[normalize-space(.)='Cadastrar']",
]

# A pagina de resultado mostra a mensagem no corpo da pagina.
MENSAGEM_RETORNO = "body"

# Botao exibido na pagina de resultado depois do cadastro, erro ou duplicidade.
BOTAO_VOLTAR_RESULTADO = "xpath=//input[normalize-space(@value)='Voltar'] | //button[normalize-space(.)='Voltar']"

# Seletor que identifica CAPTCHA ou validacao manual.
SELETOR_CAPTCHA = "iframe[src*='hcaptcha'], .h-captcha, [data-hcaptcha-widget-id]"

# Campo preenchido automaticamente apos informar a chave. Usado para aguardar o
# portal terminar o preenchimento antes de clicar em Cadastrar.
CAMPO_CONFIRMACAO_AUTOPREENCHIMENTO = "input[name='form1:j_id54']"
ESPERA_APOS_AUTOPREENCHIMENTO_MS = 500

# Mensagens exibidas no proprio formulario, antes ou depois de clicar em
# Cadastrar. A automacao tambem faz uma busca por texto caso esses seletores
# nao encontrem o alerta do portal.
MENSAGENS_VALIDACAO_FORMULARIO = [
    "[role='alert']",
    ".rf-msgs",
    ".rf-msg",
    ".rich-messages",
    ".rich-message",
    ".ui-messages",
    ".ui-message",
    ".alert",
    ".mensagem",
    ".mensagemErro",
    ".msg",
    ".msgErro",
    ".erro",
    ".error",
]

# Campo "Valor" preenchido automaticamente pelo portal.
CAMPO_VALOR_NOTA = "input[name='form1:j_id80']"

# Campo "Data Emissao" preenchido automaticamente pelo portal.
CAMPO_DATA_EMISSAO_NOTA = "input[name='form1:j_id61InputDate']"
PRAZO_MAXIMO_EMISSAO_MESES = 2

# Tempos padrao da automacao.
TIMEOUT_PADRAO_MS = 15000
TIMEOUT_RESULTADO_CADASTRO_MS = 18000
TIMEOUT_AUTOPREENCHIMENTO_MS = 6000
TIMEOUT_CLIQUE_MS = 3000
ESPERA_APOS_DIGITAR_CHAVE_MS = 250
ESPERA_APOS_CLIQUE_CADASTRAR_MS = 1200
# Ritmo conservador para evitar bloqueio por requisicoes excessivas.
PAUSA_ENTRE_NOTAS_SEGUNDOS = 0.2
PAUSA_ENTRE_NOTAS_MIN_SEGUNDOS = 4.0
PAUSA_ENTRE_NOTAS_MAX_SEGUNDOS = 8.0
INTERVALO_MINIMO_ENTRE_CADASTROS_SEGUNDOS = 6.0
PAUSA_A_CADA_N_NOTAS = 25
PAUSA_LOTE_MIN_SEGUNDOS = 30
PAUSA_LOTE_MAX_SEGUNDOS = 60
PAUSA_REQUISICOES_EXCESSIVAS_SEGUNDOS = 300
SLOW_MO_MS = 0

# Quantidade maxima de tentativas de cadastro por nota. Ao atingir este limite
# com status ERRO, a nota deixa de entrar novamente na fila automatica.
MAX_TENTATIVAS_CADASTRO = 3

# Diagnostico da automacao. Quando ativo, salva HTML, screenshots e eventos do
# navegador em logs/diagnostico para investigar falhas no clique/cadastro.
DIAGNOSTICO_ATIVO = False
DIAGNOSTICO_DIR = LOG_DIR / "diagnostico"
DIAGNOSTICO_SALVAR_HTML = True
DIAGNOSTICO_SALVAR_SCREENSHOT = True
