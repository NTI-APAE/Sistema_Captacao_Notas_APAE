# API Notas APAE

Backend FastAPI em camadas para captar e cadastrar notas fiscais.
Recebe submissões manuais e imagens por uma rota interna autenticada.

## Estrutura e responsabilidades

```text
app/
  routes/          HTTP, autenticação da integração, validação e respostas.
  schemas/         Contratos HTTP e dados de entrada/saída dos serviços.
  services/        Cadastro, consultas, worker, leitura QR e processamento de imagem.
  repositories/    SQLAlchemy, conversões e controle de transações.
  models/          Tabelas persistidas, incluindo recibos de eventos de imagem.
  domain/          Regras de estado e entidades existentes preservadas.
  infrastructure/  Configuração, dependências, logs e tratamento de exceções.
  database.py      Engine, sessão e Base SQLAlchemy.
alembic/           Migrations existentes e nova migration aditiva.
tests/             Testes de serviços e integração com SQLite temporário.
run_local.py       Inicialização local sem importar o banco da Evolution.
```

Detalhes, inventário das mudanças e ativação: [REFATORACAO.md](REFATORACAO.md).

## Entidades e transações

As entidades em `domain/` preservam as regras de transição de estado de notas e
execuções. Os modelos SQLAlchemy ficam em `models/`, e suas conversões ficam
junto aos respectivos repositórios. `repositories/contracts.py` reúne os contratos
usados pelas implementações SQLAlchemy e pelos fakes dos testes. A unidade de
trabalho mantém commit/rollback entre pessoa, nota e submissão; não há árvore de
ports/adapters ou factories adicionais.

## Casos De Uso

`RegistrarSubmissaoService`:

1. normaliza telefone;
2. valida chave fiscal com 44 dígitos;
3. busca ou cria pessoa;
4. busca ou cria nota fiscal;
5. cria sempre uma nova submissão;
6. marca submissão duplicada quando a nota já existe;
7. usa `UnitOfWork` para commit/rollback;
8. trata conflito de chave única como duplicidade concorrente.

Duplicidade retorna HTTP `201`, porque uma nova `SubmissaoNota` realmente foi
criada, apesar de a `NotaFiscal` já existir.

Também estão disponíveis:

- `ConsultarNotaService`
- `ListarNotasService`
- `ListarSubmissoesDaNotaService`
- `ConsultarPessoaService`
- `ListarNotasDaPessoaService`
- `IniciarExecucaoCadastroService`
- `RegistrarResultadoCadastroService`
- `ListarExecucoesCadastroService`
- `ReprocessarNotaService`
- `ObterProximaNotaParaProcessamentoService`
- `ConsultarExecucaoWorkerService`
- `RecuperarExecucoesExpiradasService`

`ListarNotasDaPessoaService` retorna notas únicas da pessoa: se a mesma pessoa
submeteu a mesma nota várias vezes, a nota aparece uma única vez.

## Endpoints

- `GET /health`
- `POST /submissoes`
- `POST /notas/processar-imagem` (interno, autenticado, corpo binário)
- `GET /notas`
- `GET /notas/{id}`
- `GET /notas/chave/{chave}`
- `GET /notas/{id}/submissoes`
- `POST /notas/{id}/execucoes`
- `GET /notas/{id}/execucoes`
- `POST /notas/{id}/resultado-cadastro`
- `POST /notas/{id}/reprocessar`
- `GET /pessoas/{id}`
- `GET /pessoas/telefone/{telefone}`
- `GET /pessoas/{id}/notas`
- `POST /worker/notas/proxima`
- `GET /worker/execucoes/{execucao_id}`
- `POST /worker/execucoes/{execucao_id}/resultado`

## Contrato Worker

Os endpoints `/worker/*` são o contrato oficial entre a API e o
Worker/Automatizador externo. Todos exigem o header `X-Worker-API-Key` com o
valor configurado em `WORKER_API_KEY`.

`POST /worker/notas/proxima` reserva atomicamente a próxima nota `PENDENTE`,
cria uma `ExecucaoCadastro` em `EM_EXECUCAO`, marca a nota como `CADASTRANDO` e
retorna:

```json
{
  "nota_id": "uuid",
  "execucao_id": "uuid",
  "chave": "21260912345678000123550010001234561234567890",
  "tentativa": 1
}
```

Quando não houver trabalho pendente, retorna `204 No Content`.

`POST /worker/execucoes/{execucao_id}/resultado` registra o resultado da
execução. A chamada é idempotente para repetição do mesmo resultado final e
retorna `409 Conflict` se uma execução já finalizada receber dados finais
divergentes.

```json
{
  "status": "SUCESSO",
  "mensagem": "Nota cadastrada com sucesso",
  "valor": "89.90",
  "data_emissao": "2026-08-30",
  "tempo_segundos": "8.74"
}
```

`GET /worker/execucoes/{execucao_id}` permite consultar status, tentativa,
nota vinculada e datas da execução.

O claim concorrente usa `SELECT ... FOR UPDATE SKIP LOCKED` no adapter
SQLAlchemy para PostgreSQL. O cálculo de `tentativa` continua protegido pela
constraint única `(nota_fiscal_id, tentativa)`.

Execuções em andamento antigas podem ser recuperadas chamando
`RecuperarExecucoesExpiradasService`, usando o limite configurado por
`WORKER_EXECUTION_TIMEOUT_MINUTES`. Não há scheduler embutido nesta entrega.

## Executar e testar

A partir da raiz **Projeto Bot WhatsApp Captação**:

```powershell
venv/Scripts/python.exe -m pip install -e "./api_notas_apae[dev]"
venv/Scripts/python.exe -m pip install -r EvolutionAPI/requirements.txt
```

Para ativar a nova versão, pare primeiro os dois processos Python com Ctrl+C.
Aplique a migration no banco de notas (porta local 5433); não use o `.env` da
Evolution como arquivo de ambiente da API, pois ele pode apontar para 5432.

```powershell
Push-Location api_notas_apae
../venv/Scripts/python.exe -m alembic upgrade head
Pop-Location
venv/Scripts/python.exe api_notas_apae/run_local.py
```

O inicializador lê o `.env` próprio da API, se existir. Se não houver segredo no
ambiente, lê **somente** NOTAS_INTERNAL_API_KEY ou WEBHOOK_TOKEN do `.env` da
Evolution. Não importa DATABASE_URL desse arquivo nem modifica credenciais.
Uma DATABASE_URL já definida no terminal continua tendo precedência: confirme
que aponta para o banco de notas correto antes de executar migrations.

Em outro terminal, na raiz:

```powershell
venv/Scripts/python.exe -m uvicorn EvolutionAPI.webhook:app --host 0.0.0.0 --port 8001 --env-file EvolutionAPI/.env
```

Para execução convencional, configure NOTAS_INTERNAL_API_KEY (ou WEBHOOK_TOKEN)
no ambiente da API e execute:

```powershell
venv/Scripts/python.exe -m uvicorn app.main:app --app-dir api_notas_apae --host 0.0.0.0 --port 8000
```

Swagger: http://127.0.0.1:8000/docs. Saúde: GET /health. A saúde não testa o banco.

Testes, sem Evolution ou PostgreSQL de produção:

```powershell
venv/Scripts/python.exe -m pytest api_notas_apae/tests EvolutionAPI/test_integration.py -q
Push-Location api_notas_apae
../venv/Scripts/python.exe -m ruff check app tests alembic run_local.py
../venv/Scripts/python.exe -m alembic upgrade 202609020003:head --sql
Pop-Location
```

O último comando apenas gera SQL, sem aplicá-lo.

## Pendências

As consultas administrativas e a leitura dos consentimentos são oferecidas em
endpoints JSON protegidos. Coleta de consentimentos, OCR e automação SEFAZ
continuam pendentes.
Não há fila durável ou reagendamento automático no webhook; um erro HTTP de
comunicação exige reentrega. A idempotência persistente protege a gravação quando
o mesmo evento é reenviado.

## Porta do PostgreSQL local

O banco de notas publica a porta `5433` no Windows, reservando `5432` para
o PostgreSQL da Evolution. A API e o Alembic executados no Windows usam
`localhost:5433`. No Docker Compose, a API usa `postgres:5432`.
Se definir `DATABASE_URL` no ambiente ou em `.env`, use a porta correspondente.

## Dashboard administrativo

O painel atual foi recriado em React, Next.js e TypeScript na pasta irmã
`dashboard_apae`. A API expõe consultas de leitura protegidas em
`/admin/relatorios`; as regras e agregações permanecem nos services/repositories.

O acesso usa contas administrativas persistidas no PostgreSQL, sessões opacas
revogáveis e a permissão `dashboard:read`. As chaves do webhook/worker não
autorizam o painel. Consulte `../dashboard_apae/README.md` para aplicar a
migration, criar o primeiro administrador e executar o frontend.
