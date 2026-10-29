# Deployment de produção

Este diretório prepara uma implantação controlada dos serviços de servidor. Ele
não executa deploy, não aplica migration automaticamente e não substitui o
proxy HTTPS, o firewall ou a política de backup da infraestrutura.

## Topologia

O Compose reúne os serviços de servidor para facilitar a homologação, mas mantém
perímetros separados por rede:

```text
proxy HTTPS futuro
       │
       ├── edge ── dashboard ── app_internal ── API ── notes-db
       │                         │              └── webhook
       └── edge ── API           │
                                 └── evolution_internal ── Evolution API
                                                        ├── evolution-db
                                                        └── Redis
```

O leitor desktop permanece fora do Docker e deverá acessar somente a API por um
endpoint HTTPS/VPN autorizado. PostgreSQL, Redis, Evolution API e webhook não
possuem `ports` publicados pelo Compose. A rede `edge` existe para conexão de um
proxy futuro; nenhum proxy é criado nesta tarefa.

## Pré-requisitos

- Docker Engine e Docker Compose v2;
- domínio, TLS, firewall e armazenamento de segredos definidos pela infraestrutura;
- imagem da Evolution API aprovada com tag imutável ou digest;
- volume persistente para cada banco, Redis e instâncias da Evolution;
- PostgreSQL de homologação para validar concorrência e migrations;
- credenciais administrativas criadas somente após a migration aprovada.

## Configuração de segredos

Copie os exemplos para arquivos locais não versionados:

```powershell
Copy-Item production.env.example production.env
Copy-Item evolution-api.env.example evolution-api.env
```

Substitua todos os valores `REPLACE_WITH_*` usando o secret store da
infraestrutura. `production.env` e `evolution-api.env` são ignorados pelo Git.
Não coloque credenciais reais em imagens, YAML, logs ou documentação.

`EVOLUTION_API_IMAGE`, `NOTES_DB_IMAGE`, `EVOLUTION_DB_IMAGE` e `REDIS_IMAGE`
devem apontar para versões aprovadas; `latest` não é aceito neste deployment.

## Build e inicialização

Primeiro valide a configuração sem iniciar serviços:

```powershell
docker compose --env-file production.env -f docker-compose.yml config --quiet
```

Construa as imagens e execute a migration como uma etapa explícita, com revisão
e backup aprovados pela operação:

```powershell
docker compose --env-file production.env -f docker-compose.yml build
.\migrate.ps1
```

Somente após a migration e os smoke tests:

```powershell
docker compose --env-file production.env -f docker-compose.yml up -d
docker compose --env-file production.env -f docker-compose.yml ps
```

O serviço `api` inicia apenas o Uvicorn. O serviço `migrate` existe no profile
`migration` e nunca é iniciado pelo `up` padrão.

## Healthchecks e readiness

- `GET /health` continua sendo liveness e não depende do banco;
- `GET /ready` testa `SELECT 1` no PostgreSQL e retorna `503` se a persistência
  estiver indisponível;
- os healthchecks do Compose usam `/ready` na API e endpoints locais dos demais
  serviços;
- o proxy deve encaminhar tráfego somente para serviços saudáveis.

Em produção, a documentação automática da API (`/docs`, `/redoc` e
`/openapi.json`) fica desabilitada. O acesso operacional deve ocorrer pelas
rotas necessárias e pelo proxy autorizado.

## Migrations e rollback

Revise o SQL antes da aplicação quando necessário. A migration real deve ser
executada uma única vez por janela controlada, nunca por cada réplica da API:

```powershell
docker compose --env-file production.env -f docker-compose.yml --profile migration run --rm migrate
```

Para revisão offline, use o Alembic no ambiente da API conforme o README do
componente. O rollback padrão é de aplicação: retornar a imagem anterior
compatível, manter o schema backward-compatible e validar `/ready` e os smoke
tests. Não execute `downgrade` automaticamente; downgrade de schema exige
revisão da migration, backup/restore testado e aprovação explícita.

## Operação do P0-01

O reclaimer do worker continua sendo uma operação separada:

```powershell
docker compose --env-file production.env -f docker-compose.yml run --rm api python -m app.cli.recover_worker recover
docker compose --env-file production.env -f docker-compose.yml run --rm api python -m app.cli.recover_worker list
```

O scheduler futuro deve garantir uma única instância por ambiente. Esta tarefa
não cria um scheduler nem altera as regras de recuperação do P0-01.

## Validação antes da homologação

1. `docker compose ... config --quiet` sem erro;
2. busca por credenciais fixas, `latest` e `ports` indevidos;
3. build sem `.env`, ambientes virtuais, logs ou diagnósticos;
4. migration manual em PostgreSQL isolado;
5. smoke test de `/health`, `/ready`, login, webhook e fluxo do leitor;
6. teste de reinício e rollback de aplicação;
7. validação de TLS, portas, allowlist e acesso do leitor pela infraestrutura;
8. backup/restore e RPO/RTO conforme P0-03, fora do escopo desta entrega.

## Pendências de infraestrutura

TLS, certificados, DNS, firewall, allowlist do leitor/webhook, secret store,
backup externo, observabilidade, alertas e política de retenção ainda precisam
ser definidos e homologados no ambiente real.
