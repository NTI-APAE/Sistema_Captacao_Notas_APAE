# AGENTS.md

## Escopo

Este arquivo orienta agentes que trabalham no repositório `Projeto Bot WhatsApp Captação`.
Ele se aplica à raiz e a todos os diretórios abaixo dela. Não há outro `AGENTS.md`
mais específico no momento.

Antes de editar, execute `git status --short` e preserve alterações já existentes.
O diretório de trabalho costuma conter mudanças de implementação em andamento; não
use `git reset --hard`, `git checkout --` ou comandos destrutivos para "limpar" o
estado sem autorização explícita.

## Visão geral

O repositório é um monorepo operacional composto por quatro partes:

| Diretório | Papel | Tecnologias principais |
| --- | --- | --- |
| `api_notas_apae/` | API central, regras de negócio, persistência e painel administrativo | Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, OpenCV |
| `dashboard_apae/` | Frontend administrativo | Next.js 16 App Router, React 19, TypeScript, pnpm |
| `EvolutionAPI/` | Adaptador do WhatsApp/Evolution API | FastAPI, httpx, Uvicorn |
| `Leitor Nota Fiscal/` | Aplicação desktop que importa TXT e automatiza o portal Nota Legal com intervenção humana | Python, CustomTkinter, Playwright, psycopg |

Fluxo principal:

```text
WhatsApp -> Evolution API -> EvolutionAPI/webhook.py
          -> API /notas/processar-imagem -> QR/OpenCV -> PostgreSQL

TXT -> Leitor Nota Fiscal -> API /integracao/notas/importar-txt
     -> API /worker/notas/proxima -> automação Playwright -> API /worker/.../resultado

Operador -> dashboard Next.js -> API /admin/auth e /admin/relatorios
```

## Arquitetura da API

`api_notas_apae/app/main.py` cria a aplicação e registra os routers. A separação
atual é deliberadamente simples:

- `routes/`: HTTP, autenticação de integração, dependências, status codes e respostas;
- `schemas/`: contratos de entrada/saída HTTP e DTOs de serviços;
- `services/`: casos de uso, orquestração e transações de negócio;
- `domain/`: entidades, enums, value objects e transições de estado;
- `repositories/`: contratos, implementações SQLAlchemy, mapeamento e eventos;
- `models/`: tabelas SQLAlchemy;
- `infrastructure/`: configuração, dependências, autenticação, logging e exceções;
- `database.py`: engine, `SessionLocal` e `Base`;
- `alembic/`: histórico de migrations;
- `tests/`: testes unitários e de integração.

O caminho normal de uma alteração é `route -> schema -> service -> repository/UoW`.
Não coloque regra de negócio em route handlers, não faça SQL diretamente em routes
ou no dashboard e não crie camadas/adapters/factories apenas por convenção. Os
contratos em `repositories/contracts.py` existem porque os services e os fakes dos
testes dependem deles.

Casos de uso importantes:

- `services/submissoes.py`: normaliza telefone, valida chave de 44 dígitos, cria ou
  localiza pessoa/nota e sempre registra a submissão, inclusive duplicada;
- `services/processar_imagem.py` e `services/qr_code.py`: recebem imagem, extraem
  chaves, validam formato/dígito e registram o evento de forma idempotente;
- `services/importar_notas.py`: importa chaves do leitor e reativa notas elegíveis;
- `services/worker.py` e `services/execucoes.py`: reserva notas, controla tentativas,
  estados e resultados idempotentes;
- `services/admin_reporting_service.py`: agrega dados para o dashboard.

### Contratos HTTP que não devem ser quebrados

- `GET /health`: health check simples; não pressupõe que o banco esteja saudável.
- `POST /notas/processar-imagem`: integração interna, `multipart/form-data`, limite
  de imagem de 10 MiB e header `X-Internal-API-Key`.
- `POST /integracao/notas/importar-txt`: integração interna, JSON e o mesmo header
  de integração.
- `GET /notas` e `GET /notas/{id}`: leitura operacional protegida por
  `X-Worker-API-Key`.
- `POST /worker/notas/proxima`: claim atômico; retorna `204` sem trabalho.
- `GET /worker/execucoes/{id}` e `POST /worker/execucoes/{id}/resultado`: contrato
  oficial com o automatizador. Resultado repetido igual é idempotente; resultado
  final divergente retorna `409`.
- `POST /admin/auth/login`, `GET /admin/auth/me` e `POST /admin/auth/logout`:
  sessão administrativa opaca, revogável e armazenada no PostgreSQL.
- `GET /admin/relatorios/{resumo,opcoes,notas,contatos...}`: exige sessão com
  escopo administrativo; não aceita as chaves do webhook ou do worker.

A reserva do worker usa bloqueio concorrente (`FOR UPDATE SKIP LOCKED`) no adapter
PostgreSQL e a unicidade `(nota_fiscal_id, tentativa)` protege a contagem de
tentativas. Preserve essas propriedades ao alterar repositórios ou services.

## Integrações e segurança

Existem três credenciais com responsabilidades diferentes:

- `NOTAS_API_INTERNAL_KEY`: `EvolutionAPI` e leitor desktop chamam rotas internas;
- `WORKER_API_KEY`: leitor reserva notas, consulta notas e envia resultados;
- sessão administrativa (`ADMIN_SESSION_*` / `DASHBOARD_SESSION_*`): acesso humano
  ao dashboard.

Nunca reutilize uma dessas credenciais para outra finalidade, nunca coloque segredo
em código, teste, log, URL, payload de erro ou commit. Use `.env.example` apenas
como documentação e mantenha `.env` fora do Git. O código atual de configuração do
leitor ainda possui valores fallback históricos para o portal Nota Legal; qualquer
trabalho de produção deve substituir credenciais reais por variáveis de ambiente e
não reproduzir esses valores em novos arquivos.

O webhook valida `X-Webhook-Token`, filtra mensagens próprias, grupos, broadcasts e
JIDs sem telefone, recupera a mídia na Evolution e repassa bytes/metadados à API.
Não persiste imagem nem payload bruto. Não há fila durável, retry automático ou
resposta automática ao doador; falhas transitórias dependem de reentrega do evento.

A identidade idempotente do evento de imagem é `origem=WHATSAPP + instance +
message_id`. O mesmo evento com os mesmos bytes/metadados deve ser replayado; o
mesmo identificador com outro conteúdo/remetente deve resultar em `409`. Não remova
as tabelas/migrations de eventos nem troque a chave de idempotência sem atualizar
os testes de concorrência e o contrato do webhook.

## Banco e migrations

O banco de notas usa PostgreSQL. Em desenvolvimento Windows, o Compose da API
publica normalmente `5433`; `5432` é reservado ao PostgreSQL da Evolution. Dentro
de Docker, a API usa `postgres:5432`. Confirme `DATABASE_URL` antes de executar
Alembic: uma migration aplicada no banco errado é uma falha operacional grave.

Regras para migrations:

1. criar migration aditiva em `api_notas_apae/alembic/versions/`;
2. preservar dados e compatibilidade de leitura durante a transição;
3. revisar upgrade e downgrade quando o histórico permitir;
4. testar primeiro com SQLite temporário e gerar SQL PostgreSQL offline;
5. validar em PostgreSQL de homologação antes de aplicar em uso real;
6. nunca editar uma migration já aplicada para corrigir histórico.

`api_notas_apae/run_local.py` carrega o `.env` da própria API. Se necessário,
aproveita apenas `NOTAS_API_INTERNAL_KEY` do `.env` da Evolution; não deve importar
`DATABASE_URL` da Evolution.

## Dashboard

O dashboard é um App Router Next.js. A URL interna da API e o nome/duração do cookie
ficam somente no servidor (`NOTAS_API_URL`, `DASHBOARD_SESSION_COOKIE` e
`DASHBOARD_SESSION_MINUTES`); não usar `NEXT_PUBLIC_` para eles.

O transporte em `src/lib/` encaminha apenas a sessão administrativa para a API. As
listagens devem continuar mascarando telefone e chave; detalhes continuam protegidos
e o frontend não deve receber credenciais, imagens, Base64 ou mensagens técnicas
livres. Ao mudar um contrato da API, atualize tipos, transporte, páginas e testes
do dashboard em conjunto.

## Leitor desktop

O leitor importa TXT em `leitor_txt.py`, usa `api_client.py` para falar com a API e
usa `automacao_notalegal.py`/Playwright para cadastrar notas no portal visível. Ele
não resolve nem contorna CAPTCHA: a execução deve pausar para intervenção humana.
Seletores, tempos e credenciais de ambiente ficam em `config.py`; alterações no
HTML do portal normalmente exigem mudar esses seletores e adicionar diagnóstico.

Embora o módulo se chame `database.py` e ainda aceite `DATABASE_PATH` por
compatibilidade, o código atual conecta no PostgreSQL central usando `DATABASE_URL`.
As filas, execuções e resultados oficiais vivem na API; não crie uma segunda fonte
de verdade local sem uma decisão arquitetural explícita.

O fluxo esperado do leitor é:

1. validar e deduplicar chaves do TXT;
2. enviar a importação para a API;
3. reservar uma nota no endpoint do worker;
4. executar o cadastro com navegador visível;
5. mapear o resultado do portal para o status da API;
6. enviar o resultado da execução e seguir para a próxima nota.

O portal pode retornar `CADASTRADA`, `DUPLICADA`, `IGNORADA` ou erro técnico. O
cliente converte resultados locais para os estados aceitos pela API (por exemplo,
`CADASTRADA -> SUCESSO` no payload do worker). Preserve esse mapeamento e o limite
de tentativas antes de alterar statuses.

## Comandos de desenvolvimento

Use PowerShell a partir da raiz. Os comandos abaixo assumem o ambiente existente
em `api_notas_apae\.venv`; se outro ambiente for usado, substitua o executável.

### API e webhook

```powershell
Push-Location api_notas_apae
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests alembic run_local.py
.\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location

.\api_notas_apae\.venv\Scripts\python.exe -m pytest api_notas_apae\tests EvolutionAPI\test_integration.py -q
.\api_notas_apae\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api_notas_apae --host 127.0.0.1 --port 8000
.\api_notas_apae\.venv\Scripts\python.exe -m uvicorn EvolutionAPI.webhook:app --host 0.0.0.0 --port 8001 --env-file EvolutionAPI\.env
```

`alembic upgrade head` altera o banco: confirme o ambiente e o `DATABASE_URL`
antes de executá-lo. Para apenas revisar o SQL, use:

```powershell
Push-Location api_notas_apae
.\.venv\Scripts\python.exe -m alembic upgrade 202609020003:head --sql
Pop-Location
```

### Dashboard

```powershell
Push-Location dashboard_apae
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint
pnpm test
pnpm format:check
pnpm build
pnpm dev
Pop-Location
```

### Leitor desktop

```powershell
Push-Location 'Leitor Nota Fiscal'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install
.\.venv\Scripts\python.exe main.py
Pop-Location
```

Para testes rápidos do parser, prefira importar `leitor_txt.py` com o ambiente do
leitor. Para mudanças na automação, use `DIAGNOSTICO_ATIVO` somente durante a
investigação; screenshots e HTML podem conter dados sensíveis.

## Estratégia de testes

Ao mudar a API, execute pelo menos a suíte unitária e os testes de integração
afetados. Alterações em imagem/eventos devem cobrir QR inválido, replay, conflito
de identidade, rollback e concorrência. Alterações no worker devem cobrir `204`,
claim concorrente, tentativas, timeout, idempotência e `409` conflitante. Alterações
administrativas devem cobrir login, logout, cookie, escopo e filtros/paginação.

Ao mudar o dashboard, execute typecheck, lint, testes, formatação e build quando a
alteração atingir rotas, server components ou configuração. Ao mudar o leitor,
teste o parser com QR quebrado, chave manual, linhas inválidas e duplicadas; depois
valide o cliente da API sem apontar para dados de produção.

## Checklist de entrega

- [ ] `git status` revisado e alterações preexistentes preservadas.
- [ ] Contratos HTTP, statuses e idempotência continuam documentados.
- [ ] Nenhum segredo, dado pessoal ou imagem foi adicionado a código/log/teste.
- [ ] Migration, se houver, é aditiva e foi validada no banco correto.
- [ ] Testes e verificações apropriados foram executados.
- [ ] README ou documentação do componente foi atualizada se o fluxo mudou.
- [ ] `git diff --check` não aponta whitespace inválido.
