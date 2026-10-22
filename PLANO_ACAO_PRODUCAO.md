# Plano de ação para produção

Este plano deriva da auditoria técnica e registra o que foi executado nesta
branch. A entrega cobre somente P0-02; não executa deploy real nem altera banco
de produção.

## P0-02 — deployment seguro separado

**Status:** implementação local concluída; homologação de infraestrutura pendente.

Entregas:

- Compose produtivo em `deploy/production/docker-compose.yml`;
- redes internas separadas para aplicação e Evolution;
- ausência de portas publicadas para bancos, Redis, webhook e Evolution;
- imagens versionadas por variáveis obrigatórias, sem `latest`;
- Dockerfiles produtivos para API, webhook e dashboard;
- `.dockerignore` para evitar segredos, ambientes locais, logs e diagnósticos;
- validação estrita de segredos quando `APP_ENV=production`;
- liveness `/health` e readiness `/ready`;
- migration controlada por profile e scripts dedicados;
- runbook de build, inicialização, validação e rollback;
- atualização desta auditoria e deste plano.

Validação pendente:

1. preencher os arquivos de ambiente pelo secret store;
2. confirmar a versão e a configuração da imagem Evolution;
3. executar `docker compose config`, build e smoke tests em homologação;
4. confirmar proxy HTTPS, firewall, DNS e acesso controlado do leitor;
5. ensaiar rollback de aplicação.

Verificações realizadas nesta branch: Compose sintático com valores fictícios,
Ruff da API, seis testes focados da API, TypeScript, ESLint e 18 testes locais do
dashboard passaram. A suíte completa da API teve 102/104 testes aprovados, com
duas falhas preexistentes de timezone em SQLite no worker. O format check do
dashboard apontou dois arquivos preexistentes e o build standalone encontrou
restrição `EPERM` de symlink no Windows; nenhum desses itens foi mascarado como
aprovado.

## P0-01 — recuperação do worker

**Status:** preservado; não alterado nesta tarefa.

O CLI de recuperação permanece disponível na imagem da API. Um scheduler externo
deve executar uma única instância por ambiente após a política operacional ser
aprovada.

## P0-03 — backup e restauração

**Status:** não iniciado nesta tarefa.

Ainda faltam backup criptografado, cópia fora do host, retenção, RPO/RTO,
procedimento de restore e teste cronometrado em ambiente isolado.

## P0-04 — TLS, proxy e firewall

**Status:** preparado, mas não implementado integralmente.

A rede `edge` e o runbook deixam espaço para um proxy reverso. Ainda faltam
domínio, certificados, firewall, allowlists, rate limiting e validação externa
de portas.

## Fases posteriores

Rate limiting/body limits, reconciliação do portal, LGPD, logs e retenção,
testes PostgreSQL reais, E2E do leitor, observabilidade, alertas, CI/CD e
remoção do banco legado do leitor continuam nas fases P1–P3 da auditoria.
