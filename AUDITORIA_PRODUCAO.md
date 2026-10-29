# Auditoria técnica — prontidão para produção

Este documento consolida a auditoria fornecida para o projeto e o resultado da
implementação do P0-02. A auditoria é referência de riscos; não autoriza
alterações fora do escopo solicitado.

## Veredito atual

**NÃO APTO PARA PRODUÇÃO.**

O P0-02 foi implementado em artefatos e validações estáticas nesta branch, mas a
produção ainda depende de homologação, TLS/proxy/firewall, backup/restore e
decisões de infraestrutura. O P0-01 existente foi preservado.

## Estado dos bloqueadores

| Item | Estado nesta entrega | Observação |
| --- | --- | --- |
| P0-01 — recuperação do worker | Preservado | Lease, CLI e regras permanecem sem alteração nesta tarefa; scheduler único continua pendente. |
| P0-02 — deployment seguro | Implementado estaticamente | Compose produtivo, imagens, segredos, redes, readiness e migration controlada adicionados. |
| P0-03 — backup/restore | Não implementado | Requer storage, retenção, RPO/RTO e exercício de restauração. |
| P0-04 — TLS/proxy/firewall | Preparado, não implementado | A rede `edge` está reservada; domínio, certificados e allowlist dependem da infraestrutura. |

## Evidências do P0-02

- `deploy/production/docker-compose.yml` não publica PostgreSQL, Redis, pgAdmin,
  Evolution ou webhook; serviços ficam em redes internas.
- Variáveis obrigatórias usam interpolação `${VAR:?erro}` e a API valida
  `APP_ENV=production`, chaves obrigatórias e `ADMIN_COOKIE_SECURE=true`.
- A API produtiva não executa Alembic no startup; a migration fica no profile
  explícito `migration` e nos scripts `migrate.ps1`/`migrate.sh`.
- Imagens produtivas têm Dockerfiles separados e `.dockerignore` exclui
  ambientes locais, `.env`, logs, dados e artefatos de teste.
- `GET /health` continua liveness; `GET /ready` testa o PostgreSQL.
- A documentação automática da API é desabilitada quando `APP_ENV=production`.
- Dashboard e webhook usam comunicação interna com a API; o leitor continua
  externo ao Docker e deve usar o endpoint HTTPS/VPN aprovado.

## Verificações executadas

- `docker compose config --quiet` do manifesto produtivo passou com valores
  fictícios fornecidos somente por variáveis de processo.
- Ruff da API passou.
- Os seis testes de endpoints da API, incluindo `/ready`, passaram.
- A suíte completa da API executou 104 testes: 102 passaram e 2 falharam em
  comparações de timezone já existentes nos fluxos do worker/P0-01 usando
  SQLite; essa regra não foi alterada nesta entrega.
- TypeScript, ESLint e os 18 testes locais do dashboard passaram usando os
  binários já instalados.
- O format check do dashboard apontou somente `src/components/ui.tsx` e
  `src/lib/format.ts`, arquivos preexistentes e fora desta tarefa.
- O build do dashboard compilou, mas a etapa standalone falhou por `EPERM` ao
  criar symlinks no Windows; o build de imagem Linux ainda deve ser validado.
- Nenhum deploy, migration real ou banco externo foi acessado.

## Riscos ainda abertos

1. A imagem e as variáveis específicas da Evolution API precisam ser aprovadas
   para a versão escolhida.
2. Os healthchecks da imagem externa da Evolution devem ser confirmados na
   homologação.
3. O proxy deverá restringir rotas administrativas, integrações e acesso do
   leitor, além de fornecer TLS e headers/cookies seguros.
4. Não há backup, restore, métricas, alertas, rate limiting ou testes reais de
   PostgreSQL/portal nesta entrega.
5. O leitor ainda contém código legado de banco local; ele permanece fora do
   deployment e fora do escopo P0-02.

## Critério para avançar

O veredito só deve subir para homologação após validar o Compose em ambiente
isolado, aplicar migration manualmente, confirmar os healthchecks, testar o
fluxo Evolution → webhook → API, testar o dashboard e conectar o leitor por um
endpoint controlado. Produção exige também P0-03 e P0-04 concluídos.
