# Refatoração — arquitetura em camadas

## Diagnóstico e decisões

Antes das alterações, a API separava HTTP em adapters/inbound, SQLAlchemy em
adapters/outbound, casos de uso e DTOs em application, cinco protocolos em ports
outbound e entidades em domain. Havia 42 testes passando. O webhook recuperava
a mídia, lia QR, validava dígito e enviava a chave ao POST /submissoes.

Foram preservados os contratos públicos de notas, pessoas, submissões e worker,
a normalização de telefone, a unicidade da chave, histórico de submissões,
paginação, transições de estado, tentativas de execução, reprocessamento,
reserva SKIP LOCKED no PostgreSQL e idempotência dos resultados do worker.

A API manual sempre validou somente o formato de 44 dígitos. Alterar isso nesta
refatoração invalidaria dados/contratos existentes: esse comportamento foi
preservado. A entrada por imagem mantém a validação de formato e dígito que já
existia no webhook. Nenhuma dessas validações comprova autenticidade/autorização
na SEFAZ. URLs extraídas nunca são consultadas automaticamente.

## Estrutura final

```text
api_notas_apae/
  app/
    main.py
    database.py
    routes/          health, notas, pessoas, submissões, worker, imagens
    schemas/         contratos HTTP e DTOs existentes
    services/        notas, pessoas, submissões, execuções, worker,
                     qr_code, validar_chave, processar_imagem
    repositories/    consultas SQLAlchemy, conversões, transações e eventos
    models/          modelos existentes e evento_imagem
    domain/          entidades, estados, enums e exceções existentes
    infrastructure/ configuração, injeção FastAPI, logs, segurança
  alembic/           migrations preservadas + recibos e metadados de imagem
  tests/
    unit/services/   testes anteriores reorganizados
    unit/            QR, logs e migration
    integration/     API/repositórios, imagem, concorrência e fluxo HTTP
  run_local.py
EvolutionAPI/
  webhook.py         recebe/filtra eventos e encaminha bytes
  evolution.py       recupera mídia
  notas.py           cliente da rota de imagens
  teste_webhook.py   entrada antiga compatível
  test_integration.py
  Docker/            infraestrutura existente preservada
```

Os casos de uso foram agrupados em cinco módulos de serviços. As conversões
ORM/entidade agora ficam no próprio arquivo do repositório; saiu a camada
separada de mappers. Os contratos existentes foram reunidos em contracts.py:
são mantidos porque há implementações reais e fakes usados nos testes. As
entidades com regras de transição e a unidade de trabalho permanecem para evitar
reescrever comportamento validado. Nenhum protocolo novo foi criado para a
integração de imagens, nem serviços de fila, Redis ou factories.

## Contrato entre os processos

`POST /notas/processar-imagem`

Corpo: `multipart/form-data`, máximo 10 MiB.

| Campo | Obrigatório | Conteúdo |
|---|---|---|
| imagem | sim | Arquivo binário de imagem |
| message_id | sim | ID estável da mensagem, até 255 caracteres |
| instance | sim | Instância Evolution, até 100 caracteres |
| remote_jid | sim | JID remoto recebido no evento |
| from_me | não | Booleano; o webhook não encaminha mensagens próprias |
| message_type | não | Normalmente `imageMessage` |
| timestamp | não | `data.messageTimestamp` da Evolution |
| push_name | não | `data.pushName` |
| mimetype | não | `message.imageMessage.mimetype` |
| caption | não | `message.imageMessage.caption` |
| remote_jid_alt | não | `key.remoteJidAlt`, usado para LIDs |

O header `X-Internal-API-Key` deve conter `NOTAS_API_INTERNAL_KEY`. A API usa
`instance + message_id` junto de `origem=WHATSAPP` como identidade idempotente.
O `remote_jid` é normalizado para identificar o contato; a mídia e o payload
bruto não são persistidos.

Resposta 200 inclui received, saved, replayed, qr_code_found, reason,
urls_consulta e submissoes (status, duplicada, nota_id, submissao_id). Os campos
já usados pelo webhook, received/saved/submissoes, foram preservados; os demais
são aditivos. A mídia e o payload bruto não são persistidos.

Erros: 401 credencial inválida; 409 identidade reutilizada com conteúdo diferente;
413 limite excedido; 422 dados/imagem inválidos;
503 integração não configurada ou persistência indisponível. O webhook propaga
rejeições definitivas de imagem/evento e converte falhas de comunicação em
502/504, sem confirmar salvamento. Há timeouts de 60 segundos; não há retry
interno automático. O remetente/Evolution deve reenviar após falha transitória.

## Idempotência e persistência

A migration `202609210001_eventos_imagem.py` cria o recibo de imagem. A migration
`202609300001_metadados_evento_imagem.py` acrescenta os metadados operacionais
da mensagem ao recibo e vincula cada submissão WhatsApp ao evento por
(origem, instance, message_id). Nenhuma migration anterior foi removida e a
tabela mensagens_whatsapp não foi reaproveitada: ela tem outro contrato e
unicidade global no ID.

Reserva do evento, novas pessoas/notas, todas as submissões da imagem e resultado
são confirmados juntos. Falha antes do commit reverte tudo. A PK composta resolve
concorrência no banco; conflitos de pessoa/chave também são reavaliados em nova
transação, com até três tentativas. A consulta antecipada é apenas otimização.

Mesmo evento e bytes/metadados: devolve os mesmos IDs com replayed=true.
Nova mensagem com a mesma chave: nova submissão DUPLICADA, mesma nota.
Mesmo evento com bytes/remetente diferentes: 409. Resultado sem chave também
é persistido, para não repetir processamento de imagens ilegíveis para QR.
Imagem indecodificável retorna 422 sem reservar evento.

Não há migração automática de eventos históricos: mensagens processadas antes
desta versão não têm recibo, e sua reentrega pode criar uma submissão DUPLICADA.
A imagem continua sendo recuperada na Evolution em reentregas; a API só pode
reconhecê-las depois de receber os mesmos bytes e metadados.

## Ativação e compatibilidade

As portas 8000/8001, bancos 5432/5433, nomes de containers e Compose foram
preservados nesta refatoração. Os .env reais não foram modificados. A nova API
não expõe mais POST /submissoes; o webhook usa a nova rota de
processamento de imagem e a migration correspondente. Por isso os processos ativos
NÃO foram reiniciados e
a migration NÃO foi aplicada ao banco em uso.

Siga a instalação, migration e inicialização descritas no [README](README.md).
Pare os dois processos durante a troca, aplique a migration e inicie primeiro
a API, depois o webhook. O run_local.py aproveita somente o token existente da
Evolution, sem carregar a DATABASE_URL desse arquivo (que apontava para 5432).
Variáveis do terminal e o .env próprio da API continuam tendo precedência.

Em produção, mantenha a rota em rede interna ou restrinja-a no proxy; a chave
interna é obrigatória mesmo na rede local. Em containers, injete a chave no
ambiente da API. O Compose não foi modificado para incluir segredos.
Os logs de acesso ocultam chaves/telefones em caminhos e removem query strings.

## Arquivos migrados/consolidados

Os caminhos antigos abaixo foram removidos somente depois da migração das
responsabilidades e da passagem dos testes. Os __init__.py vazios e diretórios
antigos de application/adapters também foram removidos.

| Arquivo(s) anterior(es), relativos à API | Destino |
|---|---|
| `app/adapters/inbound/http/routes/health_routes.py` | `app/routes/health_routes.py` |
| `app/adapters/inbound/http/routes/notas_routes.py` | `app/routes/notas_routes.py` |
| `app/adapters/inbound/http/routes/pessoas_routes.py` | `app/routes/pessoas_routes.py` |
| `app/adapters/inbound/http/routes/submissao_routes.py` | `app/routes/submissao_routes.py` |
| `app/adapters/inbound/http/routes/worker_routes.py` | `app/routes/worker_routes.py` |
| `app/adapters/inbound/http/schemas/execucao_schemas.py` | `app/schemas/execucao_schemas.py` |
| `app/adapters/inbound/http/schemas/nota_schemas.py` | `app/schemas/nota_schemas.py` |
| `app/adapters/inbound/http/schemas/pessoa_schemas.py` | `app/schemas/pessoa_schemas.py` |
| `app/adapters/inbound/http/schemas/submissao_history_schemas.py` | `app/schemas/submissao_history_schemas.py` |
| `app/adapters/inbound/http/schemas/submissao_schemas.py` | `app/schemas/submissao_schemas.py` |
| `app/adapters/inbound/http/schemas/worker_schemas.py` | `app/schemas/worker_schemas.py` |
| `app/application/dto/execucao_cadastro_input.py` | `app/schemas/execucao_cadastro_input.py` |
| `app/application/dto/execucao_cadastro_output.py` | `app/schemas/execucao_cadastro_output.py` |
| `app/application/dto/nota_output.py` | `app/schemas/nota_output.py` |
| `app/application/dto/pagination.py` | `app/schemas/pagination.py` |
| `app/application/dto/pessoa_output.py` | `app/schemas/pessoa_output.py` |
| `app/application/dto/registrar_submissao_input.py` | `app/schemas/registrar_submissao_input.py` |
| `app/application/dto/registrar_submissao_output.py` | `app/schemas/registrar_submissao_output.py` |
| `app/application/dto/submissao_output.py` | `app/schemas/submissao_output.py` |
| `app/application/dto/worker_output.py` | `app/schemas/worker_output.py` |
| `app/adapters/outbound/persistence/sqlalchemy/models/all_models.py` | `app/models/all_models.py` |
| `app/adapters/outbound/persistence/sqlalchemy/models/base.py` | `app/models/base.py` |
| `app/adapters/outbound/persistence/sqlalchemy/models/execucao_cadastro_model.py` | `app/models/execucao_cadastro_model.py` |
| `app/adapters/outbound/persistence/sqlalchemy/models/nota_fiscal_model.py` | `app/models/nota_fiscal_model.py` |
| `app/adapters/outbound/persistence/sqlalchemy/models/pessoa_model.py` | `app/models/pessoa_model.py` |
| `app/adapters/outbound/persistence/sqlalchemy/models/submissao_nota_model.py` | `app/models/submissao_nota_model.py` |
| `app/adapters/outbound/persistence/sqlalchemy/database.py` | `app/database.py` |
| `app/adapters/outbound/persistence/sqlalchemy/unit_of_work.py` | `app/repositories/unit_of_work.py` |
| `app/application/exceptions.py` | `app/repositories/exceptions.py` |
| `app/application/ports/outbound/pessoa_repository.py`<br>`app/application/ports/outbound/nota_repository.py`<br>`app/application/ports/outbound/submissao_repository.py`<br>`app/application/ports/outbound/execucao_repository.py`<br>`app/application/ports/outbound/unit_of_work.py` | `app/repositories/contracts.py` |
| `app/adapters/outbound/persistence/sqlalchemy/mappers/nota_mapper.py`<br>`app/adapters/outbound/persistence/sqlalchemy/repositories/nota_repository.py` | `app/repositories/nota_repository.py` |
| `app/adapters/outbound/persistence/sqlalchemy/mappers/pessoa_mapper.py`<br>`app/adapters/outbound/persistence/sqlalchemy/repositories/pessoa_repository.py` | `app/repositories/pessoa_repository.py` |
| `app/adapters/outbound/persistence/sqlalchemy/mappers/submissao_mapper.py`<br>`app/adapters/outbound/persistence/sqlalchemy/repositories/submissao_repository.py` | `app/repositories/submissao_repository.py` |
| `app/adapters/outbound/persistence/sqlalchemy/mappers/execucao_mapper.py`<br>`app/adapters/outbound/persistence/sqlalchemy/repositories/execucao_repository.py` | `app/repositories/execucao_repository.py` |
| `app/application/use_cases/consultar_nota.py`<br>`app/application/use_cases/listar_notas.py`<br>`app/application/use_cases/listar_notas_da_pessoa.py`<br>`app/application/use_cases/listar_submissoes_da_nota.py`<br>`app/application/use_cases/reprocessar_nota.py` | `app/services/notas.py` |
| `app/application/use_cases/consultar_pessoa.py` | `app/services/pessoas.py` |
| `app/application/use_cases/registrar_submissao.py` | `app/services/submissoes.py` |
| `app/application/use_cases/execucoes_cadastro.py` | `app/services/execucoes.py` |
| `app/application/use_cases/worker.py` | `app/services/worker.py` |

Outras mudanças:

- Criados: models/evento_imagem.py, repositories/eventos.py, schemas/imagem.py,
  routes/imagens.py, services/processar_imagem.py, services/qr_code.py,
  services/validar_chave.py, run_local.py, migration 202609210001 e novos testes.
- Modificados: main.py, infrastructure/dependencies.py, config.py e logging.py,
  alembic/env.py, pyproject.toml, .env.example, README.md e imports dos testes.
- EvolutionAPI: alterados webhook.py, evolution.py, notas.py, requirements.txt,
  test_integration.py, .env.example e README.md. qr_code.py removido após migração.
- Criado este relatório. Mapa completo acima inclui rotas, schemas, DTOs,
  repositórios, transações, modelos e serviços antigos.
- As diferenças de porta 5433 em relação ao Git são anteriores a esta tarefa.

## Validação e limites

A suíte de regressão original tinha 42 testes. A suíte final inclui QR real com
OpenCV, as cinco etapas de leitura, imagens inválidas/sem QR, extração e dígito,
autenticação, duplicidade de nota, replay, concorrência, rollback de lote,
integração HTTP com transporte simulado e resposta perdida depois do commit.

A nova migration foi testada em SQLite temporário preservando dados existentes,
e a cadeia Alembic foi compilada para SQL PostgreSQL em modo offline. As
integrações de persistência usam SQLite temporário; isso não substitui uma
validação de concorrência no PostgreSQL de homologação. Nada foi aplicado ao
PostgreSQL em uso. Teste real com uma nova mensagem fica para depois da ativação.

O dashboard administrativo exibe instância, ID/JID, data/hora da mensagem,
atraso até o processamento, legenda, MIME, tipo, reenvios do mesmo evento e o
histórico de mensagens diferentes que geraram a mesma nota. Não foram
implementados OCR, resposta automática ao doador, scheduler ou cadastro SEFAZ.
Não há fila durável; falhas precisam de
reentrega. O limite de 10 MiB é de bytes comprimidos, não de memória decodificada:
para exposição a tráfego não confiável ainda é recomendável limitar recursos do
processo OpenCV. As URLs retornadas são texto não confiável, nunca consultadas.

Resultado final: **92 testes passaram**; Ruff da API e do webhook sem erros;
`git diff --check` sem erros; SQL da migration PostgreSQL gerado com sucesso.
Há dois avisos de depreciação do TestClient/Starlette, sem falhas.
O inicializador também foi verificado sem subir servidor: segredo carregado e
DATABASE_URL da Evolution não importada; destino local confirmado em 5433.
