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
