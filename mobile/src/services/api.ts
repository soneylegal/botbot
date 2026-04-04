import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const api = axios.create({
  // Ajuste para IP local quando testar no device físico.
  baseURL: API_BASE_URL,
  timeout: 8000,
});

let accessToken = '';
let refreshToken = '';
let isRefreshing = false;

async function ensureAuth() {
  if (accessToken) return;
  const email = 'admin@botbot.local';
  const password = 'admin123';

  try {
    const { data } = await axios.post<{ access_token: string; refresh_token?: string }>(`${API_BASE_URL}/auth/login`, { email, password });
    accessToken = data.access_token;
    refreshToken = data.refresh_token ?? '';
  } catch {
    await axios.post(`${API_BASE_URL}/auth/register`, { email, password });
    const { data } = await axios.post<{ access_token: string; refresh_token?: string }>(`${API_BASE_URL}/auth/login`, { email, password });
    accessToken = data.access_token;
    refreshToken = data.refresh_token ?? '';
  }
}

api.interceptors.request.use(async (config) => {
  await ensureAuth();
  config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error?.response?.status !== 401 || original?._retry) {
      throw error;
    }

    if (!refreshToken || isRefreshing) {
      accessToken = '';
      throw error;
    }

    try {
      isRefreshing = true;
      const { data } = await axios.post<{ access_token: string; refresh_token?: string }>(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      accessToken = data.access_token;
      refreshToken = data.refresh_token ?? refreshToken;
      original._retry = true;
      original.headers.Authorization = `Bearer ${accessToken}`;
      return api(original);
    } finally {
      isRefreshing = false;
    }
  }
);

export function getMarketWsUrl(asset: string) {
  const wsBase = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsBase}/ws/market/${asset}`;
}

export type DashboardData = {
  status: string;
  daily_pnl: number;
  asset?: string;
  chart: Array<{ t: string; p: number }>;
};

export type StrategyConfig = {
  id?: string;
  asset: string;
  timeframe: string;
  ma_short_period: number;
  ma_long_period: number;
};

export type BacktestData = {
  period_label: string;
  metrics: {
    total_return: number;
    win_rate: number;
    max_drawdown: number;
    sharpe_ratio: number;
  };
  equity_curve: number[];
};

export type LogRow = {
  id: number;
  level: 'success' | 'error' | 'info' | 'warning';
  message: string;
  created_at: string;
};

export type SettingsData = {
  api_key_masked?: string;
  api_secret_masked?: string;
  exchange_name: string;
  trade_mode: 'paper' | 'live';
  paper_trading: boolean;
  dark_mode: boolean;
};

export type PaperState = {
  balance: number;
  open_position_asset?: string;
  open_position_qty: number;
  recent_orders: Array<{
    id: number;
    side: 'buy' | 'sell';
    asset: string;
    price: number;
    quantity: number;
    status: string;
    created_at: string;
  }>;
};

export async function fetchDashboard() {
  const { data } = await api.get<DashboardData>('/dashboard');
  return data;
}

export async function fetchStrategy() {
  const { data } = await api.get<StrategyConfig>('/strategy/config');
  return data;
}

export async function saveStrategy(payload: StrategyConfig) {
  const { data } = await api.put<StrategyConfig>('/strategy/config', payload);
  return data;
}

export async function fetchBacktest() {
  const { data } = await api.get<BacktestData>('/backtest/results');
  return data;
}

export async function runBacktest(period_label = '6 Months') {
  const { data } = await api.post<BacktestData>('/backtest/run', { period_label });
  return data;
}

export async function fetchLogs() {
  const { data } = await api.get<LogRow[]>('/logs?limit=100');
  return data;
}

export async function fetchSettings() {
  const { data } = await api.get<SettingsData>('/settings');
  return data;
}

export async function saveSettings(payload: {
  api_key?: string;
  api_secret?: string;
  exchange_name: string;
  trade_mode: 'paper' | 'live';
  paper_trading: boolean;
  dark_mode: boolean;
}) {
  const { data } = await api.put<SettingsData>('/settings', payload);
  return data;
}

export async function testConnection() {
  const { data } = await api.post<{ ok: boolean; message: string }>('/settings/test-connection');
  return data;
}

export async function fetchPaperState() {
  const { data } = await api.get<PaperState>('/paper/state');
  return data;
}

export async function paperBuy(payload: { asset: string; price: number; quantity: number }) {
  const { data } = await api.post('/paper/buy', payload);
  return data;
}

export async function paperSell(payload: { asset: string; price: number; quantity: number }) {
  const { data } = await api.post('/paper/sell', payload);
  return data;
}
