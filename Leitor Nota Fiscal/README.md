# Leitor Nota Fiscal - Nota Legal

Aplicacao desktop em Python para importar chaves de notas fiscais a partir de TXT, enviar a fila para a API Notas APAE, gerar relatorios e executar uma automacao assistida no portal Nota Legal.

O sistema nao burla CAPTCHA. Quando houver CAPTCHA ou validacao manual, a automacao pausa e aguarda a intervencao humana no navegador visivel.

## Requisitos

- Python 3.11 ou superior
- Windows, Linux ou macOS
- API Notas APAE em execução
- Navegadores do Playwright instalados

## Instalar

Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependencias:

```powershell
pip install -r requirements.txt
```

Instale os navegadores do Playwright:

```powershell
playwright install
```

Configure no ambiente do leitor:

```powershell
NOTAS_API_URL=http://127.0.0.1:8000
NOTAS_API_INTERNAL_KEY=chave-interna-configurada-na-API
WORKER_API_KEY=chave-do-worker-configurada-na-API
```

Se precisar usar outro servidor, altere `NOTAS_API_URL` antes de iniciar o app.

## Rodar

```powershell
python main.py
```

O banco é administrado somente pela API; o leitor grava apenas logs locais em `logs/sistema.log`.

Ao concluir cada operação de automação, o leitor envia à API um resumo idempotente
com o identificador do lote, quantidades e valores totais separados por
`CADASTRADA`, `DUPLICADA`, `IGNORADA` e `ERRO`. A API persiste esses dados para o
dashboard administrativo; o envio usa `NOTAS_API_INTERNAL_KEY`.

## Gerar ZIP para outra maquina

Para gerar um pacote completo com executavel, Chromium do Playwright e `venv` com dependencias, execute:

```powershell
.\criar_zip_distribuicao.ps1
```

Ou clique duas vezes em:

```text
criar_zip_distribuicao.bat
```

O arquivo final sera criado em:

```text
dist\Leitor Nota Fiscal - Com Venv.zip
```

Na outra maquina, extraia o ZIP inteiro e abra `Leitor Nota Fiscal.exe`. Nao envie nem mova somente o `.exe`, porque a automacao precisa das pastas `_internal` e `ms-playwright`.

O ZIP tambem inclui a pasta `venv` e o arquivo `Executar pelo venv.bat` para teste opcional pelo codigo-fonte. Para uso normal, prefira o executavel.

O ZIP nao inclui banco local. Todas as maquinas devem apontar para a mesma API usando `NOTAS_API_URL` e as chaves de integração.

## Seletores configurados

Os seletores em `config.py` foram preenchidos com base nas telas enviadas:

```python
URL_LOGIN = "https://sistemas1.sefaz.ma.gov.br/portalnotalegal/jsp/login/login.jsf"
PREENCHER_LOGIN_AUTOMATICO = True
LOGIN_CPF_CNPJ = os.getenv("NOTALEGAL_LOGIN_CPF_CNPJ", "")
LOGIN_SENHA = os.getenv("NOTALEGAL_LOGIN_SENHA", "")
LOGIN_PERFIL_TEXTO = "Entidades Beneficentes"
ESPERA_ANTES_PREENCHER_LOGIN_MS = 3000
TIMEOUT_CAMPO_LOGIN_MS = 3000
CAMPO_LOGIN_CPF_CNPJ = ""
CAMPO_LOGIN_SENHA = ""
RADIO_LOGIN_PERFIL = ""
MENU_CADASTRAR_NOTAS = "text=Cadastrar Notas"
CAMPO_TIPO_NOTA = "select[name='form1:j_id45']"
TIPO_NOTA_TEXTO = "NFCE - NOTA FISCAL AO CONSUMIDOR ELETR\u00d4NICA"
CAMPO_CHAVE = "input[name='form1:j_id49']"
BOTAO_CONSULTAR = ""
BOTAO_SALVAR = "input[id='form1:j_id97']"
USAR_A4J_DIRETO_CADASTRAR = True
A4J_FORM_CADASTRAR = "form1"
A4J_BOTAO_CADASTRAR = "form1:j_id97"
BOTAO_SALVAR_FALLBACKS = [
    "input.botao_sistema[value='Cadastrar']",
    "xpath=//input[normalize-space(@value)='Cadastrar' and @type='button']",
    "xpath=//button[normalize-space(.)='Cadastrar']",
]
MENSAGEM_RETORNO = "body"
BOTAO_VOLTAR_RESULTADO = "xpath=//input[normalize-space(@value)='Voltar'] | //button[normalize-space(.)='Voltar']"
SELETOR_CAPTCHA = "iframe[src*='hcaptcha'], .h-captcha, [data-hcaptcha-widget-id]"
CAMPO_CONFIRMACAO_AUTOPREENCHIMENTO = "input[name='form1:j_id54']"
ESPERA_APOS_AUTOPREENCHIMENTO_MS = 500
MENSAGENS_VALIDACAO_FORMULARIO = [
    "[role='alert']",
    ".rf-msgs",
    ".rich-messages",
    ".ui-messages",
    ".alert",
    ".mensagemErro",
    ".msgErro",
    ".erro",
    ".error",
]
CAMPO_VALOR_NOTA = "input[name='form1:j_id80']"
MAX_TENTATIVAS_CADASTRO = 3
TIMEOUT_RESULTADO_CADASTRO_MS = 18000
TIMEOUT_AUTOPREENCHIMENTO_MS = 6000
TIMEOUT_CLIQUE_MS = 3000
ESPERA_APOS_DIGITAR_CHAVE_MS = 250
ESPERA_APOS_CLIQUE_CADASTRAR_MS = 1200
PAUSA_ENTRE_NOTAS_SEGUNDOS = 0.2
PAUSA_ENTRE_NOTAS_MIN_SEGUNDOS = 4.0
PAUSA_ENTRE_NOTAS_MAX_SEGUNDOS = 8.0
INTERVALO_MINIMO_ENTRE_CADASTROS_SEGUNDOS = 6.0
PAUSA_A_CADA_N_NOTAS = 25
PAUSA_LOTE_MIN_SEGUNDOS = 30
PAUSA_LOTE_MAX_SEGUNDOS = 60
PAUSA_REQUISICOES_EXCESSIVAS_SEGUNDOS = 300
SLOW_MO_MS = 0
DIAGNOSTICO_ATIVO = False
```

Se o portal mudar a tela, ajuste os seletores no `config.py` apos inspecionar os campos no navegador.

## Fluxo da automacao

1. Abre o portal em navegador visivel.
2. Preenche automaticamente **Informe o CPF/CNPJ**, **Senha de Acesso** e seleciona **Entidades Beneficentes**.
3. O usuario resolve o CAPTCHA manualmente e clica em **Acessar**.
4. Depois do login, o usuario clica em **Continuar** na aplicacao.
5. O sistema clica em **Cadastrar Notas**.
6. Seleciona **NFCE - NOTA FISCAL AO CONSUMIDOR ELETRONICA** em **Tipo da Nota**.
7. Aguarda o campo **Chave** aparecer.
8. Preenche a chave da nota.
9. Aguarda o preenchimento automatico dos demais campos.
10. Clica em **Cadastrar**.
11. Le a pagina de resultado.
12. Clica em **Voltar** para cadastrar a proxima nota.

Mensagens reconhecidas:

- `Nota cadastrada com sucesso no nota legal!`: marca como `CADASTRADA`.
- `Atencao Esta nota ja foi doada`: marca como `DUPLICADA`.
- `Numero da chave Invalida, por favor verificar novamente`: marca como `IGNORADA`, para nao tentar novamente em execucoes futuras.
- `As notas nao podem ter sido emitidas a mais de 2 meses`: marca como `IGNORADA`.

Quando essas mensagens aparecem no proprio formulario, antes da pagina final de conclusao, a automacao captura o texto, salva no banco, atualiza a tabela e pula para a proxima nota sem insistir no botao **Cadastrar**.

As mensagens do portal sao gravadas na coluna `mensagem` da tabela `notas` com o texto exibido pelo site, sem trocar por uma descricao generica do sistema. Mensagens tecnicas internas continuam identificadas como erro tecnico.

## Formato do TXT

O TXT aceita dois formatos por linha.

Formato vindo de QR Code, com a chave no trecho entre `p=` e o primeiro separador `}` ou `]`:

```text
httpÇ;;nfce.sefaz.ma.gov.br;portal:COSULTARNFce.jsp;p=21260562738733000185650010000331081002115464}2}1}1}33174de2086339968b34c8c12d809beb1f00704b
```

Resultado extraido:

```text
21260562738733000185650010000331081002115464
```

Formato digitado manualmente, contendo somente a chave numerica:

```text
21260462738733000185650010000311121004108082
21260462738733000185650010000313931004084034
21260462738733000185650010000311381004797402
```

Linhas vazias sao ignoradas, linhas sem chave valida sao contabilizadas como invalidas e chaves repetidas nao sao importadas duas vezes.

O leitor tambem aceita alguns padroes quebrados por leitores de QR Code:

- QR Code usando `]` no lugar de `}`;
- URL truncada comecando em `nfce.s...`, quando ainda existe uma sequencia numerica antes de `}` ou `]`;
- duas URLs coladas na mesma linha;
- chave quebrada por quebra de linha logo depois de `p=`.

## Usar o sistema

1. Clique em **Selecionar arquivo TXT**.
2. Confirme o caminho exibido no campo da tela.
3. Clique em **Processar arquivo**; as chaves são enviadas para `POST /integracao/notas/importar-txt`.
4. Confira totais, logs e tabela de notas carregada da API central.
5. Clique em **Iniciar automacao**.
6. O navegador abre visivel com CPF/CNPJ, senha e perfil preenchidos.
7. Resolva o CAPTCHA manualmente e clique em **Acessar** no portal.
8. Clique em **Continuar** para liberar o processamento.
9. Se a automacao detectar CAPTCHA ou validacao manual durante o uso, ela pausa. Resolva no navegador e clique em **Continuar**.

A aplicação reserva notas `PENDENTE`, `ERRO_CADASTRO` ou `PAUSADA` pelo endpoint do Worker. Ao reservar uma nota para uma instância do app, ela fica temporariamente como `CADASTRANDO`, evitando que outra instância pegue a mesma nota. Ao fechar e abrir novamente, notas já `CADASTRADA`, `DUPLICADA` ou `IGNORADA` não são repetidas automaticamente.

Notas com status `ERRO` sao tentadas novamente ate `MAX_TENTATIVAS_CADASTRO`. Depois da terceira falha, a nota continua registrada como `ERRO`, recebe uma mensagem de limite atingido e deixa de entrar na fila automatica, permitindo que a automacao siga para a proxima.

Se uma chave ja existente for importada novamente e estiver com status `ERRO` ou `IGNORADA`, ela sera reativada para novo envio: volta para `PENDENTE`, zera as tentativas e entra novamente na fila da automacao. Chaves ja `CADASTRADA` ou `DUPLICADA` continuam protegidas contra repeticao.

Na aba **Operacao**, a tabela mostra as notas adicionadas ou reativadas no dia atual e tambem todas as notas que ainda estao na fila de cadastro, mesmo que tenham sido importadas em outro dia. A automacao processa essa fila ao iniciar.

A tela de operacao mostra contadores em tempo real:

- fila pendente;
- notas cadastradas hoje;
- total de notas cadastradas no banco.

Os botoes **Pausar** e **Continuar** sao separados. O botao **Excluir fila** remove notas `PENDENTE`, `ERRO`, `PROCESSANDO`, `PAUSADA` e `AGUARDANDO_CAPTCHA` da fila, preservando notas `CADASTRADA`, `DUPLICADA` e `IGNORADA`.

Para evitar encerramento de sessao por requisicoes excessivas, a automacao usa intervalo minimo entre cadastros, pausa aleatoria entre notas e pausa maior por lote. Se o portal exibir `Requisicoes excessivas detectadas. Sessao encerrada.`, o sistema pausa, aguarda o tempo configurado e pede novo login manual antes de continuar.

## Diagnostico

Com `DIAGNOSTICO_ATIVO = True`, a automacao salva evidencias em `logs/diagnostico`. Deixe desativado no uso normal, porque screenshots e HTML a cada nota deixam o processo mais lento.

- screenshots antes de clicar em **Cadastrar**;
- screenshots depois do resultado ou erro;
- HTML da pagina;
- JSON com URL, texto da tela, campos e estado do botao;
- eventos de console, erros JavaScript, falhas de rede e respostas Ajax em `eventos.log`.

Use isso para investigar por que o portal nao saiu da tela de cadastro ou por que uma mensagem foi classificada de certo modo.

## Status

- `PENDENTE`
- `CADASTRADA`
- `DUPLICADA`
- `ERRO`
- `IGNORADA`
- `AGUARDANDO_CAPTCHA`
- `PAUSADA`
- `PROCESSANDO`

## Relatorios

Na aba **Relatorios**:

1. Informe data inicial e final no formato brasileiro `DD/MM/AAAA`, por exemplo `10/06/2026`.
2. Clique em **Atualizar**.
3. Confira o resumo por dia.
4. Confira no resumo principal os campos **Fora Prazo**, **Valor Fora Prazo** e **Valor Erros**.
5. No dashboard administrativo, consulte os valores totais e separados por status
   no bloco de operações do leitor.
6. Na lista de teste manual, copie as notas com status `IGNORADA` ou `ERRO`.
7. Clique em **Exportar Excel** ou **Exportar relatorio**.
8. Use **Limpar relatorio** para apagar o historico dos relatorios sem remover a fila pendente.

O botao **Limpar relatorio** remove notas `CADASTRADA`, `DUPLICADA`, `IGNORADA` e `ERRO` que ja atingiram o limite de tentativas. Notas ainda pendentes ou aptas para nova tentativa sao preservadas.

O Excel gerado contem:

- Aba **Resumo por dia**: data, cadastradas, valor cadastrado, fora do prazo, valor fora do prazo, duplicadas, erros, valor total das notas com erro, ignoradas, pendentes e total.
- Aba **Detalhamento**: somente notas `IGNORADA` e `ERRO`, com codigo da nota fiscal, valor, status, mensagem, arquivo de origem, data de importacao, data de cadastro e tentativa.

A tela de relatorios tambem permite copiar uma nota selecionada ou todos os codigos exibidos para teste manual.

## Persistencia

Os dados ficam no PostgreSQL administrado pela API. O leitor não cria nem
atualiza um banco local.

O progresso e salvo a cada nota processada. Em caso de erro tecnico em uma nota, ela e marcada como `ERRO` e a automacao continua para a proxima.

## Conformidade

Este projeto automatiza apenas etapas assistidas e repetitivas. Ele nao tenta resolver, quebrar, contornar ou evitar CAPTCHA. Qualquer CAPTCHA ou validacao manual deve ser resolvido pelo usuario no navegador visivel.
