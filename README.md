# Sistema de Captação e Processamento de Notas Fiscais

Sistema operacional da APAE para receber imagens de notas fiscais pelo WhatsApp,
extrair suas chaves de acesso, importar notas por arquivo TXT e acompanhar o
processamento em um painel administrativo.

O sistema é composto por uma API central, um adaptador para a Evolution API, um
leitor desktop para automação assistida do portal Nota Legal e um dashboard web.
Os dados oficiais ficam no PostgreSQL da API; o leitor não mantém uma fila local.

## Fluxo geral

```text
WhatsApp
   │
   ▼
EvolutionAPI ── webhook ──► API central ──► PostgreSQL
                                  │
                                  ├── QR Code / OCR
                                  ├── submissões e eventos idempotentes
                                  └── fila do worker

Arquivo TXT ──► Leitor desktop ──► importação na API
                                      │
                                      ▼
                              reserva de nota no worker
                                      │
                                      ▼
                           portal Nota Legal visível
                           (CAPTCHA resolvido por humano)

Operador ──► Dashboard Next.js ──► relatórios administrativos da API
```

## Componentes

### `api_notas_apae/`

API FastAPI responsável por:

- persistência e regras de negócio das notas, pessoas e submissões;
- leitura de QR Code e fallback de OCR;
- controle idempotente de eventos recebidos pelo WhatsApp;
- importação de chaves vindas do leitor desktop;
- fila concorrente de processamento e registro de execuções;
- autenticação das integrações e sessões administrativas;
- relatórios consumidos pelo dashboard.

### `EvolutionAPI/`

Adaptador do WhatsApp/Evolution API. Valida o token do webhook, ignora mensagens
próprias, grupos, broadcasts e remetentes sem telefone, recupera a imagem na
Evolution e a envia para a API central com os metadados da mensagem.

### `Leitor Nota Fiscal/`

Aplicação desktop em Python que:

1. lê e valida chaves em arquivos TXT;
2. envia a importação para a API;
3. reserva uma nota pelo endpoint do worker;
4. abre o navegador visível para o portal Nota Legal;
5. aguarda intervenção humana em CAPTCHA ou validações manuais;
6. envia o resultado da execução de volta para a API.

### `dashboard_apae/`

Dashboard Next.js protegido por sessão administrativa. Exibe indicadores,
notas, contatos, relatórios filtrados, histórico de mensagens WhatsApp e opções
de impressão/exportação CSV.

## Credenciais e limites de acesso

As credenciais têm responsabilidades separadas:

- `NOTAS_API_INTERNAL_KEY`: EvolutionAPI e leitor, para rotas de integração;
- `WORKER_API_KEY`: leitor, para reservar notas e enviar resultados;
- sessão administrativa: dashboard e relatórios humanos.

Nunca coloque valores reais em código, commits, logs ou documentação. Use os
arquivos `.env.example` como referência e mantenha os arquivos `.env` fora do
Git.

Principais contratos protegidos:

| Uso | Endpoint | Credencial |
| --- | --- | --- |
| Health check | `GET /health` | nenhuma |
| Imagem do WhatsApp | `POST /notas/processar-imagem` | `X-Internal-API-Key` |
| Importação TXT | `POST /integracao/notas/importar-txt` | `X-Internal-API-Key` |
| Fila do leitor | `POST /worker/notas/proxima` | `X-Worker-API-Key` |
| Resultado da execução | `POST /worker/execucoes/{id}/resultado` | `X-Worker-API-Key` |
| Relatórios | `GET /admin/relatorios/...` | sessão administrativa |

As imagens têm limite de 10 MiB. O evento de imagem é identificado por
`origem + instância + message_id`; reenvios do mesmo conteúdo são idempotentes e
um mesmo identificador com conteúdo diferente é rejeitado.

## Requisitos

- Windows, Linux ou macOS;
- Python 3.12 ou superior para a API;
- Python 3.11 ou superior para o leitor;
- PostgreSQL;
- Node.js e pnpm para o dashboard;
- Tesseract OCR instalado quando o fallback de OCR for necessário;
- navegadores do Playwright instalados no leitor.

Em desenvolvimento Windows, a API costuma acessar o PostgreSQL na porta `5433`.
A Evolution API usa normalmente a porta `5432`. Confirme sempre o
`DATABASE_URL` antes de executar migrations.

## Configuração rápida

Copie os exemplos de ambiente para arquivos locais e preencha os valores fora do
Git:

```powershell
Copy-Item EvolutionAPI\.env.example EvolutionAPI\.env
Copy-Item api_notas_apae\.env.example api_notas_apae\.env
```

No leitor, configure pelo ambiente ou por `Leitor Nota Fiscal\.env`:

```text
NOTAS_API_URL=http://127.0.0.1:8000
NOTAS_API_INTERNAL_KEY=mesma-chave-interna-da-API
WORKER_API_KEY=mesma-chave-do-worker-da-API
NOTALEGAL_LOGIN_CPF_CNPJ=seu-cpf-ou-cnpj
NOTALEGAL_LOGIN_SENHA=sua-senha
```

As credenciais do portal são usadas apenas para preenchimento assistido. O
CAPTCHA e a confirmação de acesso continuam sendo responsabilidade do operador.

## Executar localmente

### API

```powershell
Push-Location api_notas_apae
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Pop-Location
```

Para revisar o SQL de uma migration sem aplicá-la:

```powershell
Push-Location api_notas_apae
.\.venv\Scripts\python.exe -m alembic upgrade 202609020003:head --sql
Pop-Location
```

### Evolution API

```powershell
.\api_notas_apae\.venv\Scripts\python.exe -m uvicorn EvolutionAPI.webhook:app `
  --host 0.0.0.0 --port 8001 --env-file EvolutionAPI\.env
```

Configure na Evolution a URL do webhook como:

```text
http://localhost:8001/webhook/whatsapp
```

### Dashboard

```powershell
Push-Location dashboard_apae
pnpm install --frozen-lockfile
pnpm dev
Pop-Location
```

O dashboard usa a URL interna da API somente no servidor. Não transforme
`NOTAS_API_URL` ou credenciais em variáveis `NEXT_PUBLIC_*`.

### Leitor desktop

```powershell
Push-Location 'Leitor Nota Fiscal'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install
.\.venv\Scripts\python.exe main.py
Pop-Location
```

## Testes e qualidade

API e Evolution:

```powershell
.\api_notas_apae\.venv\Scripts\python.exe -m pytest `
  api_notas_apae\tests EvolutionAPI\test_integration.py -q
```

```powershell
Push-Location api_notas_apae
.\.venv\Scripts\python.exe -m ruff check app tests alembic run_local.py
Pop-Location
```

Dashboard:

```powershell
Push-Location dashboard_apae
pnpm typecheck
pnpm lint
pnpm test
pnpm format:check
pnpm build
Pop-Location
```

Ao alterar o leitor, valide também o parser de TXT, a comunicação com a API e
o fluxo de resultado da automação. Não execute testes apontando para dados de
produção.

## Banco e migrations

As migrations ficam em `api_notas_apae/alembic/versions/`. Crie migrations
aditivas, preserve a compatibilidade durante transições e valide primeiro em
SQLite temporário e em PostgreSQL de homologação. Nunca edite uma migration já
aplicada em um ambiente real.

O claim do worker usa bloqueio concorrente no PostgreSQL (`FOR UPDATE SKIP
LOCKED`) e a unicidade de nota/tentativa protege a contagem de execuções. Essas
propriedades devem ser preservadas em alterações futuras.

## Estrutura resumida

```text
api_notas_apae/
├── app/routes/          HTTP e autenticação de rotas
├── app/services/        casos de uso e transações
├── app/domain/          entidades, enums e regras de estado
├── app/repositories/    contratos e persistência SQLAlchemy
├── app/models/          modelos do banco
├── alembic/              migrations
└── tests/                testes unitários e de integração

EvolutionAPI/             adaptador do webhook WhatsApp
Leitor Nota Fiscal/       cliente desktop e automação assistida
dashboard_apae/           painel Next.js
```

Para detalhes específicos de cada componente, consulte os respectivos
`README.md` e o `AGENTS.md` da raiz.
