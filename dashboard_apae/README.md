# Dashboard APAE

Painel administrativo do Bot WhatsApp de Captação de Notas Fiscais, criado em
React 19, Next.js 16 (App Router) e TypeScript. Este projeto fica separado da
API e consome exclusivamente os endpoints de leitura em `/admin/relatorios`.

## Estado atual

A interface, os filtros, a paginação, os gráficos, as telas de detalhes e o login
administrativo estão implementados. A API valida o usuário no PostgreSQL e cria
uma sessão revogável com o escopo `dashboard:read`.

Não use as chaves do webhook ou do worker como login do painel. Elas identificam
integrações de máquina e não um operador administrativo.

## Pré-requisitos

- Node.js 22.12 ou superior;
- pnpm 11;
- API `api_notas_apae` em execução;
- PostgreSQL da API atualizado com as migrations existentes;
- migration `202609280001` aplicada e pelo menos um administrador criado.

## Configuração

Copie `.env.example` para `.env.local` e ajuste a URL interna da API:

```dotenv
NOTAS_API_URL=http://127.0.0.1:8000
DASHBOARD_SESSION_COOKIE=apae_session
DASHBOARD_SESSION_MINUTES=480
```

Essas variáveis são exclusivas do servidor Next.js. Não adicione o prefixo
`NEXT_PUBLIC_`, pois a URL interna e o nome da sessão não precisam ser enviados
ao navegador.

O Next.js encaminha à API somente o cookie configurado em
`DASHBOARD_SESSION_COOKIE`. Os nomes e a duração devem coincidir com
`ADMIN_SESSION_COOKIE` e `ADMIN_SESSION_MINUTES` da API.

## Criar o primeiro administrador

Atualize o banco e execute o comando no terminal da API. A senha é solicitada
sem aparecer na tela e armazenada somente como hash Argon2:

```powershell
..\venv\Scripts\python.exe -m alembic upgrade head
..\venv\Scripts\python.exe -m app.cli.create_admin --nome "Administrador APAE" --email "admin@apae.org.br"
```

Use `--role LEITURA` para uma conta apenas de consulta. Após cinco senhas
incorretas, a conta fica bloqueada por 15 minutos.

## Executar em desenvolvimento

Em um terminal, inicie a API:

```powershell
Set-Location "C:\Users\yan.garrido\Documents\Projeto Bot WhatsApp Captação\api_notas_apae"
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Em outro terminal, inicie o dashboard:

```powershell
Set-Location "C:\Users\yan.garrido\Documents\Projeto Bot WhatsApp Captação\dashboard_apae"
pnpm install
pnpm dev
```

Abra `http://127.0.0.1:3000`. A página inicial apresenta o sistema e direciona
o usuário ao login. Após a autenticação, o painel abre em `/dashboard`.

## Produção

```powershell
pnpm install --frozen-lockfile
pnpm build
pnpm start
```

Execute o frontend e a API atrás do proxy HTTPS da organização. Encaminhe ao
Next.js apenas o cookie administrativo `HttpOnly`, `Secure` e `SameSite`
apropriado. Restrinja a API à rede interna e não exponha os endpoints de painel
sem o middleware de autenticação.

## Páginas

- `/`: apresentação pública do sistema;
- `/login`: autenticação administrativa;
- `/dashboard`: indicadores, volume dos últimos 30 dias e últimos recebimentos;
- `/dashboard/notas`: filtros e paginação de submissões;
- `/dashboard/relatorios`: filtros, indicadores, impressão e exportação CSV das notas recebidas;
- `/dashboard/notas/{submissao_id}`: detalhe do recebimento, metadados da mensagem WhatsApp e histórico de reenvios/duplicidades;
- `/dashboard/contatos`: filtros, consentimentos atuais e contagens;
- `/dashboard/contatos/{pessoa_id}`: dados, histórico e notas enviadas.

Listagens recebem telefone e chave já mascarados pela API. Os valores completos
só aparecem nas telas de detalhe, que também exigem autenticação. O frontend não
recebe payloads, imagens, Base64, mensagens técnicas livres ou credenciais.

## Verificação

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm format:check
pnpm build
```

O projeto inclui testes para filtros preservados na URL, paginações independentes,
datas em Brasília, transporte sem cache, encaminhamento da sessão, respostas de
autenticação, falhas da API, respostas não JSON e URLs de backend inválidas.

## Checklist para uso real

1. Aplicar `alembic upgrade head`.
2. Criar o primeiro administrador pelo comando acima.
3. Configurar as variáveis da API e do Next.js com o mesmo cookie/duração.
4. Validar consultas e desempenho no PostgreSQL de homologação com dados reais.
5. Publicar API e frontend atrás de HTTPS com `ADMIN_COOKIE_SECURE=true`.
6. Executar uma validação de aceite com os operadores da APAE.
