# Resumo do sistema de captação e processamento de notas fiscais

**Revisão:** 07/10/2026

**Escopo:** estado atual do repositório `Projeto Bot WhatsApp Captação`.

Este documento consolida o que está implementado no sistema, como os componentes
se integram, quais contratos estão disponíveis e quais validações foram executadas
neste estado do código.

## Visão geral

O sistema operacional da APAE é formado por quatro componentes:

1. **API central (`api_notas_apae/`)**: regras de negócio, persistência,
   processamento de imagens, fila do worker e relatórios administrativos.
2. **Adaptador WhatsApp (`EvolutionAPI/`)**: recebe eventos da Evolution API,
   recupera mídias e encaminha imagens e metadados à API central.
3. **Leitor desktop (`Leitor Nota Fiscal/`)**: importa chaves de arquivos TXT e
   executa o cadastro assistido no portal Nota Legal com navegador visível.
4. **Dashboard (`dashboard_apae/`)**: painel web administrativo em Next.js para
   indicadores, notas, contatos e relatórios.

O PostgreSQL da API é a fonte oficial dos dados. O leitor desktop não mantém uma
fila local independente; ele consulta, reserva e atualiza notas diretamente pela
API.

## Fluxos implementados

### Recebimento pelo WhatsApp

```text
WhatsApp
  -> Evolution API
  -> EvolutionAPI/webhook.py
  -> recuperação dos bytes da mídia
  -> POST /notas/processar-imagem
  -> leitura QR/OCR e validação da chave
  -> pessoa, nota, submissão e evento persistidos no PostgreSQL
```

O webhook filtra mensagens próprias, grupos, broadcasts, instâncias diferentes e
remetentes sem telefone identificável. JIDs do tipo LID podem usar
`remoteJidAlt` para recuperar o telefone.

### Importação e cadastro pelo leitor

```text
Arquivo TXT
  -> parser e deduplicação local
  -> POST /integracao/notas/importar-txt
  -> POST /worker/notas/proxima
  -> navegador visível no portal Nota Legal
  -> CAPTCHA/validações resolvidos pelo operador
  -> POST /worker/execucoes/{id}/resultado
```

O leitor mapeia os resultados do portal para os estados aceitos pela API e segue
para a próxima nota conforme as regras de tentativas.

### Operação administrativa

```text
Operador
  -> login administrativo
  -> sessão opaca revogável em cookie HttpOnly
  -> dashboard Next.js
  -> /admin/relatorios/*
  -> indicadores, filtros, detalhes, contatos e exportações
```

## API central

### Arquitetura

A API usa FastAPI, SQLAlchemy 2, Alembic e PostgreSQL, com separação entre:

- `routes/`: HTTP, autenticação, validação e códigos de resposta;
- `schemas/`: contratos de entrada e saída;
- `services/`: casos de uso e orquestração transacional;
- `domain/`: entidades, value objects, enums e transições de estado;
- `repositories/`: contratos, repositórios SQLAlchemy, mapeamento e unidade de
  trabalho;
- `models/`: tabelas persistidas;
- `infrastructure/`: configuração, segurança, dependências, logs e exceções.

As transações de pessoa, nota e submissão usam unidade de trabalho com commit e
rollback. A chave fiscal é única no banco, enquanto cada recebimento continua
registrado como uma nova submissão, inclusive quando a nota é duplicada.

### Domínio e estados

As entidades centrais são `Pessoa`, `NotaFiscal`, `SubmissaoNota`,
`ProcessamentoNota` e `ExecucaoCadastro`.

Estados implementados:

- **Nota:** `PENDENTE`, `CADASTRANDO`, `AGUARDANDO_CAPTCHA`, `PAUSADA`,
  `CADASTRADA`, `DUPLICADA`, `IGNORADA`, `ERRO_CADASTRO`;
- **Submissão:** `RECEBIDA`, `PROCESSANDO`, `CHAVE_EXTRAIDA`, `PENDENTE`,
  `DUPLICADA`, `ERRO_LEITURA`;
- **Execução:** `PENDENTE`, `EM_EXECUCAO`, `AGUARDANDO_CAPTCHA`, `PAUSADA`,
  `SUCESSO`, `DUPLICADA`, `IGNORADA`, `ERRO`.

As transições inválidas são rejeitadas pelo domínio. Também estão implementados
reprocessamento de notas elegíveis, controle de tentativas e recuperação de
execuções antigas por timeout.

### Processamento de imagem e chave fiscal

`POST /notas/processar-imagem` implementa:

- autenticação por `X-Internal-API-Key`;
- recebimento `multipart/form-data`;
- limite de imagem de 10 MiB;
- leitura de QR Code usando OpenCV;
- fallback de OCR somente quando o QR não produz uma chave válida;
- recorte/priorização da região acima do QR para OCR;
- extração e validação de chave fiscal com 44 dígitos e dígito verificador;
- normalização do telefone a partir dos metadados da mensagem;
- persistência atômica do lote de submissões;
- retorno estruturado para imagem processável, imagem sem chave, replay ou erro.

URLs encontradas no conteúdo não são consultadas automaticamente e não são
tratadas como prova de autenticidade ou autorização na SEFAZ.

### Idempotência de eventos do WhatsApp

A identidade do evento é composta por:

```text
origem + instância + message_id
```

O recibo persistido em `eventos_imagem` guarda fingerprint, resultado e metadados,
mas não armazena a imagem nem o payload bruto do WhatsApp.

- Reenvio do mesmo evento com o mesmo conteúdo: resultado anterior é devolvido e
  o processamento não é repetido.
- Mesmo identificador com conteúdo, remetente ou metadados incompatíveis: `409`.
- Evento concorrente: há proteção para que apenas uma gravação seja confirmada.
- Mensagem enviada pelo próprio bot: ignorada sem gerar submissão.

### Importação de TXT

`POST /integracao/notas/importar-txt` recebe as chaves extraídas pelo leitor e
retorna totais de linhas, válidas, inválidas, duplicadas, inseridas, reativadas e
já existentes.

O serviço:

- cria notas novas como `PENDENTE`;
- preserva notas já cadastradas ou duplicadas contra repetição automática;
- reativa notas elegíveis em erro ou ignoradas, zerando a tentativa quando
  aplicável;
- mantém a importação dentro de uma transação.

Ao concluir uma operação, o leitor envia `POST /integracao/leitor/resumos` com
um `operacao_id`, quantidades, valores e tempos agregados por resultado. O
endpoint é idempotente: o mesmo resumo pode ser reenviado, enquanto um mesmo
`operacao_id` com dados diferentes retorna `409 Conflict`. Esses resumos são
persistidos para os indicadores do dashboard e podem ser consultados em
`GET /admin/relatorios/resumo` e `GET /admin/relatorios/leitor`.

### Fila e contrato do worker

Todas as rotas `/worker/*` exigem `X-Worker-API-Key`.

- `POST /worker/notas/proxima`: reserva atomicamente uma nota pendente, cria uma
  execução, marca a nota como em cadastro e retorna `204` quando não há trabalho.
- `GET /worker/execucoes/{execucao_id}`: consulta status e dados da execução.
- `POST /worker/execucoes/{execucao_id}/resultado`: recebe o resultado do portal,
  valor, data de emissão, mensagem e tempo de execução.

No PostgreSQL, a reserva usa `FOR UPDATE SKIP LOCKED`. A constraint única
`(nota_fiscal_id, tentativa)` protege a contagem de tentativas em concorrência.

Resultados finais repetidos e idênticos são idempotentes. Um resultado diferente
para uma execução já finalizada retorna `409 Conflict`.

### Consultas operacionais

As rotas `GET /notas` e `GET /notas/{id}` também exigem a chave do worker e
suportam paginação, status, período, telefone e chave fiscal. A API aplica a
regra de que notas de uma mesma pessoa são listadas sem duplicação quando a
consulta é por pessoa.

### Autenticação administrativa

Rotas disponíveis:

- `POST /admin/auth/login`;
- `GET /admin/auth/me`;
- `POST /admin/auth/logout`.

A autenticação administrativa implementa:

- senha armazenada com hash Argon2;
- sessão opaca armazenada por hash no PostgreSQL;
- expiração, revogação e atualização do último uso;
- cookie `HttpOnly`, `SameSite=Strict` e `Secure` configurável;
- bloqueio temporário após cinco falhas de senha;
- escopo `dashboard:read` para acesso aos relatórios.

As chaves de integração do WhatsApp e do worker não autorizam o dashboard.

### Relatórios administrativos

As rotas protegidas por sessão são:

- `GET /admin/relatorios/resumo`;
- `GET /admin/relatorios/opcoes`;
- `GET /admin/relatorios/notas`;
- `GET /admin/relatorios/notas/{submissao_id}`;
- `GET /admin/relatorios/contatos`;
- `GET /admin/relatorios/contatos/{pessoa_id}`;
- `GET /admin/relatorios/leitor`.

Os relatórios agregam indicadores, recebimentos por dia, status de submissões,
status de cadastro, notas, mensagens WhatsApp, contatos, consentimentos e
histórico por pessoa.

As listagens mascaram telefone e chave. Detalhes continuam protegidos por sessão
e o frontend não recebe imagens, Base64, credenciais ou mensagens técnicas livres.
Respostas de erro do painel são padronizadas e não expõem detalhes de banco ou
exceções internas.

### Rotas públicas e de integração

| Método | Rota | Proteção | Finalidade |
| --- | --- | --- | --- |
| `GET` | `/health` | Nenhuma | Health check simples |
| `POST` | `/notas/processar-imagem` | `X-Internal-API-Key` | Receber imagem e metadados |
| `POST` | `/integracao/notas/importar-txt` | `X-Internal-API-Key` | Importar chaves do leitor |
| `POST` | `/integracao/leitor/resumos` | `X-Internal-API-Key` | Registrar resumo de operação do leitor |
| `GET` | `/notas` | `X-Worker-API-Key` | Listar notas operacionalmente |
| `GET` | `/notas/{id}` | `X-Worker-API-Key` | Consultar uma nota |
| `POST` | `/worker/notas/proxima` | `X-Worker-API-Key` | Reservar trabalho |
| `GET` | `/worker/execucoes/{id}` | `X-Worker-API-Key` | Consultar execução |
| `POST` | `/worker/execucoes/{id}/resultado` | `X-Worker-API-Key` | Registrar resultado |

## Banco e migrations

O schema inclui pessoas, notas fiscais, submissões, execuções de cadastro,
eventos de imagem, usuários administrativos e sessões administrativas.

Migrations presentes:

1. `202609020001_initial_schema`;
2. `202609020002_add_phase2_indexes`;
3. `202609020003_decimal_tempo_execucao`;
4. `202609210001_eventos_imagem`;
5. `202609280001_sessoes_admin`;
6. `202609300001_metadados_evento_imagem`;
7. `202610070001_resumos_operacao_leitor`.

As alterações recentes de eventos e sessões são aditivas. A aplicação de
migrations deve ser feita no banco correto, respeitando a diferença entre a porta
local `5433` da API e a porta `5432` normalmente usada pela Evolution.

## Adaptador WhatsApp / Evolution API

O componente `EvolutionAPI` implementa:

- endpoint de webhook para eventos `MESSAGES_UPSERT`;
- validação de `X-Webhook-Token`;
- validação da instância configurada;
- filtragem de mensagens próprias, grupos, broadcasts e remetentes inválidos;
- recuperação da mídia em Base64 na Evolution;
- limite de 10 MiB para a mídia;
- encaminhamento multipart para a API central;
- repasse de `message_id`, instância, JID, JID alternativo, timestamp, nome,
  MIME type, legenda e tipo de mensagem;
- tratamento de timeout, rejeição, resposta malformada e falha de comunicação;
- preservação da semântica de reentrega do evento.

O componente não persiste imagens e não registra payloads sensíveis nos logs.
Não há fila durável, retry interno automático ou resposta automática ao doador.
Quando a comunicação falha, o evento depende de reentrega da Evolution ou de
intervenção operacional.

## Leitor desktop de notas

### Parser de TXT

O leitor aceita:

- chave fiscal digitada em linha numérica;
- QR Code com trecho entre `p=` e `}` ou `]`;
- QR quebrado/truncado iniciado por `nfce.s...`;
- duas URLs coladas na mesma linha;
- quebra de linha logo após `p=`.

Linhas vazias são ignoradas, linhas inválidas são contabilizadas e chaves
duplicadas dentro do arquivo são importadas uma única vez.

### Cliente da API

`api_client.py` implementa chamadas para:

- importar o TXT com a credencial interna;
- listar e consultar notas com a credencial do worker;
- reservar a próxima execução;
- enviar resultado com status, mensagem, valor, data de emissão e tempo;
- converter estados locais do portal para o contrato oficial da API.

O mapeamento principal é:

| Portal/leitor | API worker |
| --- | --- |
| `CADASTRADA` | `SUCESSO` |
| `DUPLICADA` | `DUPLICADA` |
| `IGNORADA` | `IGNORADA` |
| `ERRO` | `ERRO` |
| `AGUARDANDO_CAPTCHA` | `AGUARDANDO_CAPTCHA` |
| `PAUSADA` | `PAUSADA` |

### Automação assistida

O Playwright usa navegador visível e executa as etapas de login, seleção do perfil,
abertura de cadastro, preenchimento da chave, leitura do resultado e retorno para
a próxima nota.

O sistema não resolve nem contorna CAPTCHA. Ao detectar CAPTCHA ou validação
manual, pausa e aguarda o operador. Também reconhece resultados de nota cadastrada,
duplicada, chave inválida, nota fora do prazo e erros técnicos.

Há controle de:

- até três tentativas configuradas para cadastro;
- pausa e continuação manuais;
- pausa por excesso de requisições;
- intervalo mínimo e pausas aleatórias entre notas;
- pausa maior por lote;
- atualização do status e progresso após cada nota;
- diagnóstico opcional com screenshots, HTML, console, rede e Ajax.

### Interface e relatórios do leitor

A aplicação CustomTkinter oferece:

- seleção e processamento de TXT;
- contadores de fila, cadastradas no dia e total cadastradas;
- tabela operacional alimentada pela API;
- início, pausa, continuação e exclusão da fila elegível;
- aba de relatórios por período;
- detalhamento de notas ignoradas e com erro;
- cópia de chaves para teste manual;
- exportação para Excel;
- limpeza de histórico sem remover notas ainda pendentes ou aptas a nova tentativa.

## Dashboard web

O dashboard usa React 19, Next.js 16 App Router, TypeScript e componentes de
servidor.

Páginas implementadas:

- `/`: apresentação do sistema;
- `/login`: login administrativo;
- `/dashboard`: indicadores, volume dos últimos 30 dias, recebimentos recentes e
  resumo persistido das operações do leitor;
- `/dashboard/notas`: filtros e paginação de submissões;
- `/dashboard/notas/{submissao_id}`: detalhe, metadados do WhatsApp e histórico;
- `/dashboard/relatorios`: indicadores, filtros, impressão e exportação CSV;
- `/dashboard/contatos`: contatos, consentimentos e contagens;
- `/dashboard/contatos/{pessoa_id}`: detalhe, histórico e notas enviadas.

O middleware protege `/dashboard/*`. O transporte server-side encaminha somente o
cookie administrativo para a API, usa `no-store` e normaliza erros sem vazar
detalhes internos. Filtros, paginação e períodos são preservados na URL.

## Segurança e privacidade

As três credenciais têm responsabilidades separadas:

- `NOTAS_API_INTERNAL_KEY`: integrações internas, como Evolution e leitor;
- `WORKER_API_KEY`: reserva e atualização de execuções;
- sessão administrativa: uso humano do dashboard.

Também estão implementados:

- comparação segura de chaves de integração;
- ausência de credenciais em URL, payload de erro ou log;
- mascaramento de telefone e chave em listagens administrativas;
- logs com redaction de caminhos, query strings e dados sensíveis;
- não armazenamento de imagens ou payload bruto do WhatsApp;
- cookies administrativos com atributos de segurança configuráveis;
- respostas administrativas sem detalhes técnicos livres.

## Validações executadas nesta revisão

Os comandos foram executados no estado atual do repositório:

- **API:** `98 passed` na suíte pytest;
- **API/Ruff:** todos os checks aprovados;
- **EvolutionAPI:** `12` testes de integração aprovados;
- **Dashboard:** `18` testes unitários aprovados;
- **Dashboard typecheck:** aprovado;
- **Dashboard lint:** aprovado;
- **Dashboard format:check:** aprovado;
- **Dashboard build:** aprovado com Next.js 16.3.6;
- **Git:** árvore de trabalho limpa e `git diff --check` sem problemas.

Os testes da API cobrem, entre outros pontos, QR válido e inválido, OCR,
limite de imagem, replay, conflito de identidade, concorrência, rollback,
importação, autenticação, relatórios, claim concorrente do worker, `204`,
tentativas, timeout, idempotência e `409` conflitante.

Os testes do dashboard cobrem autenticação, cookie, filtros, paginação, datas em
Brasília, transporte sem cache, erros HTTP, respostas não JSON e rejeição de URLs
de backend inválidas.

Não foi encontrada uma suíte automatizada dedicada ao leitor desktop. A automação
do portal depende de navegador, credenciais configuradas e intervenção humana;
por isso, seu funcionamento completo deve ser validado em homologação com o
portal acessível.

## Dependências e limitações operacionais

- PostgreSQL deve estar disponível e a `DATABASE_URL` precisa apontar para o banco
  correto antes de executar Alembic ou iniciar a API.
- O fallback de OCR requer o executável Tesseract instalado e, se necessário,
  `TESSERACT_CMD` configurado.
- O leitor requer Playwright e navegadores instalados.
- Credenciais do portal Nota Legal devem vir do ambiente; não devem ser gravadas no
  código ou no repositório.
- CAPTCHA, confirmações e validações manuais continuam sob responsabilidade do
  operador.
- O webhook é síncrono e não possui fila durável ou retry automático próprio.
- A recuperação de execuções expiradas existe como serviço, mas não há scheduler
  embutido nesta entrega.
- A leitura de chave fiscal valida formato e dígito; não consulta a SEFAZ para
  comprovar autenticidade.

## Comandos principais

### API e integração

```powershell
Push-Location api_notas_apae
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests alembic run_local.py
Pop-Location

.\api_notas_apae\.venv\Scripts\python.exe -m pytest api_notas_apae\tests EvolutionAPI\test_integration.py -q
```

### Dashboard

```powershell
Push-Location dashboard_apae
pnpm typecheck
pnpm lint
pnpm test
pnpm format:check
pnpm build
Pop-Location
```

### Leitor

```powershell
Push-Location 'Leitor Nota Fiscal'
python -m playwright install
python main.py
Pop-Location
```

Antes de usar em produção, aplicar as migrations no PostgreSQL de homologação,
criar o primeiro administrador, configurar as três credenciais separadas e
validar o fluxo completo com operadores da APAE.
