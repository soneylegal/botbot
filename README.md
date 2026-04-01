# Bot de Swing Trade - Starter Full-Stack

Estrutura inicial com:

- Backend/API: FastAPI (Python)
- Banco: PostgreSQL
- Frontend Mobile: React Native (Expo + TypeScript)

## Estrutura

- backend/ → API e regras iniciais
- mobile/ → app React Native com telas e navegação
- db/schema.sql → schema PostgreSQL

## 1) Banco PostgreSQL

Crie o banco e rode o schema:

1. Crie um banco `swingbot` no PostgreSQL.
2. Execute o arquivo [db/schema.sql](db/schema.sql).

## 2) Backend (FastAPI)

No diretório backend:

1. Copie `.env.example` para `.env` e ajuste `DATABASE_URL`.
2. Instale dependências:
   - `pip install -r requirements.txt`
3. Rode a API:
   - `uvicorn app.main:app --reload --port 8000`

Swagger: http://localhost:8000/docs

## 3) Mobile (React Native)

No diretório mobile:

1. Instale dependências:
   - `npm install`
2. Rode o app:
   - `npm run start`

Defina a URL da API em [mobile/src/services/api.ts](mobile/src/services/api.ts).

## Telas implementadas

- Dashboard (gráfico em tempo real mock + status + P/L diário)
- Configuração da Estratégia (ativo, timeframe, sliders de MAs)
- Backtesting (gráfico e métricas)
- Logs e Notificações (lista colorida)
- Settings (API Key/Secret mascarados, toggles, teste conexão)
- Paper Trading (Buy/Sell, saldo, posição e ordens recentes)
