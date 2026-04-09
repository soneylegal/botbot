# Bot de Swing Trade - Starter Full-Stack

Estrutura inicial com:

- Backend/API: FastAPI (Python)
- Banco: PostgreSQL
- Frontend Mobile: React Native (Expo + TypeScript)

## Estrutura

- backend/ → API e regras iniciais
- mobile/ → app React Native com telas e navegação
- db/schema.sql → schema PostgreSQL
- docker-compose.yml → orquestra PostgreSQL + Backend

## Execução rápida (recomendado)

Suba banco + API com Docker Compose (sem mobile):

1. Na raiz do projeto, rode:
   - `docker compose up --build -d`
2. API disponível em:
   - http://localhost:8000
3. Swagger:
   - http://localhost:8000/docs

O PostgreSQL é inicializado automaticamente com [db/schema.sql](db/schema.sql).

### Reinicializar banco do zero

Para apagar volume e reexecutar o schema:

- `docker compose down -v`
- `docker compose up --build -d`

## Execução manual (alternativa)

Use este modo apenas se não quiser Docker para backend/banco.

### 1) Banco PostgreSQL

Crie o banco e rode o schema:

1. Crie um banco `swingbot` no PostgreSQL.
2. Execute o arquivo [db/schema.sql](db/schema.sql).

### 2) Backend (FastAPI)

No diretório backend:

1. Copie `.env.example` para `.env` e ajuste `DATABASE_URL`.
2. Instale dependências:
   - `pip install -r requirements.txt`
3. Rode a API:
   - `uvicorn app.main:app --reload --port 8000`

Swagger: http://localhost:8000/docs

### Recursos implementados no backend

- JWT Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`
- Rotas protegidas por Bearer token (dashboard/strategy/backtest/logs/settings/paper)
- WebSocket de mercado: `ws://localhost:8000/ws/market/{ASSET}`
- Backtest com pandas: `POST /backtest/run`
- Integração exchange (paper/live) com `ccxt`

Usuário seed de desenvolvimento:

- email: `admin@botbot.local`
- senha: `admin123`

## 3) Mobile (React Native)

No diretório mobile:

1. Instale dependências:
   - `npm install`
2. Rode o app:
   - `npm run start`

Defina a URL da API com variável de ambiente:

- `EXPO_PUBLIC_API_BASE_URL=http://localhost:8000`

Exemplo (web):

- `EXPO_PUBLIC_API_BASE_URL=http://localhost:8000 npm run start`

No app, a tela inicial agora é de autenticação (não carrega dashboard sem JWT).

> Em device físico, troque `localhost` pelo IP da máquina.

> O mobile não está dockerizado por design.

## Telas implementadas

- Dashboard (gráfico em tempo real via WebSocket + status + P/L diário)
- Configuração da Estratégia (ativo, timeframe, sliders de MAs)
- Backtesting (gráfico, métricas e execução via botão)
- Logs e Notificações (lista colorida)
- Settings (API Key/Secret, exchange, modo paper/live, toggles, teste conexão)
- Paper Trading (Buy/Sell, saldo, posição e ordens recentes)

## Deploy no Microsoft Azure (preparado)

Este repositório já está preparado para deploy com Azure Developer CLI (AZD) usando Azure Container Apps.

Arquivos criados para deploy:

- `azure.yaml`
- `infra/main.bicep`
- `infra/main.parameters.json`
- `.azure/plan.copilotmd`

### Arquitetura alvo

- Backend FastAPI em Azure Container Apps
- Banco em Azure Database for PostgreSQL Flexible Server
- Azure Container Registry para imagem Docker
- User Assigned Managed Identity para acesso seguro
- Azure Key Vault para secrets (`DATABASE_URL`, `JWT_SECRET_KEY`)
- Application Insights + Log Analytics para observabilidade

### Pré-requisitos

1. Azure CLI e AZD instalados
2. Login no Azure:
   - `az login`
   - `azd auth login`

### Passo a passo

1. Na raiz do projeto:
   - `azd env new dev`
2. Defina os segredos do ambiente:
   - `azd env set POSTGRES_ADMIN_PASSWORD <senha-forte>`
   - `azd env set JWT_SECRET_KEY <chave-jwt-forte>`
3. Faça um preview da infraestrutura:
   - `azd provision --preview`
4. Provisione e faça o deploy:
   - `azd up`

### Pós-deploy

- Pegue a URL pública do backend gerada pelo `azd up`.
- No mobile Expo, configure:
  - `EXPO_PUBLIC_API_BASE_URL=<url-do-backend-no-azure>`

## Deploy via GitHub Actions

Workflows já adicionados:

- `.github/workflows/azure-preview.yml` (preview em pull request)
- `.github/workflows/azure-deploy.yml` (deploy em push para main ou manual)

### 1) Configurar autenticação OIDC (GitHub -> Azure)

1. Crie um App Registration no Microsoft Entra ID.
2. Crie um Service Principal para esse app.
3. Adicione credenciais federadas para o repositório:
   - Branch `main` (deploy)
   - Pull Request (preview)

### 2) Permissões do Service Principal

No escopo da assinatura ou do resource group alvo, atribua:

- `Contributor`
- `User Access Administrator`

Observação: `User Access Administrator` é necessário porque o Bicep cria role assignments (AcrPull e Key Vault Secrets User).

### 3) Secrets no GitHub Repository

Em Settings > Secrets and variables > Actions, criar:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `POSTGRES_ADMIN_PASSWORD`
- `JWT_SECRET_KEY`

### 4) Ajustar região (opcional)

Os workflows usam `eastus` por padrão. Para mudar, edite `AZURE_LOCATION` nos arquivos de workflow.

### 5) Fluxo de execução

1. Abra PR para `main`: o workflow de preview executa `azd provision --preview`.
2. Merge em `main`: o workflow de deploy executa:
   - preparação de ambiente azd
   - `azd provision --preview`
   - `azd up`
   - health check em `/health`

### 6) Mobile após deploy

Atualize no app mobile:

- `EXPO_PUBLIC_API_BASE_URL=https://<fqdn-do-container-app>`
