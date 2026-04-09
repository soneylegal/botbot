import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const envApiBaseUrl = (
  globalThis as { process?: { env?: { EXPO_PUBLIC_API_BASE_URL?: string } } }
).process?.env?.EXPO_PUBLIC_API_BASE_URL;

const API_BASE_URL =
  envApiBaseUrl ??
  (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');

export const api = axios.create({
  // Ajuste para IP local quando testar no device físico.
  baseURL: API_BASE_URL,
  timeout: 8000,
});

let accessToken = '';
let refreshToken = '';
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];
const UI_CACHE_PREFIX = 'botbot:ui:';

async function clearVisualCache() {
  try {
    const keys = await AsyncStorage.getAllKeys();
    const visualKeys = keys.filter((k) => k.startsWith(UI_CACHE_PREFIX));
    if (visualKeys.length > 0) {
      await Promise.all(visualKeys.map((k) => AsyncStorage.removeItem(k)));
    }
  } catch {
    // non-blocking
  }
}

export async function clearVisualCacheOnColdStart() {
  await clearVisualCache();
}

export async function clearVisualCacheOnTokenRefresh() {
  await clearVisualCache();
}

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export function setAuthTokens(tokens: { access_token: string; refresh_token?: string }) {
  accessToken = tokens.access_token;
  refreshToken = tokens.refresh_token ?? '';
}

export function clearAuthTokens() {
  accessToken = '';
  refreshToken = '';
}

export function hasAuthToken() {
  return Boolean(accessToken);
}

export async function loginWithCredentials(email: string, password: string) {
  const { data } = await axios.post<{ access_token: string; refresh_token?: string }>(`${API_BASE_URL}/auth/login`, { email, password });
  setAuthTokens(data);
  return data;
}

export async function registerUser(email: string, password: string) {
  await axios.post(`${API_BASE_URL}/auth/register`, { email, password });
}

api.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  console.log('[API][REQ]', config.method?.toUpperCase(), config.url, {
    hasToken: Boolean(accessToken),
    hasRefresh: Boolean(refreshToken),
  });
  return config;
});

api.interceptors.response.use(
  (response) => {
    console.log('[API][RES]', response.status, response.config?.url, response.data);
    return response;
  },
  async (error: AxiosError) => {
    const errPayload = error.response?.data ?? error.message;
    console.log('[API][ERR]', error.response?.status ?? 'NETWORK', error.config?.url, errPayload);
    const original = error.config as RetryableRequestConfig | undefined;
    if (!original) {
      throw error;
    }

    if (error?.response?.status !== 401 || original._retry) {
      throw error;
    }

    if (!refreshToken) {
      clearAuthTokens();
      throw error;
    }

    if (isRefreshing) {
      const token = await new Promise<string>((resolve) => {
        refreshSubscribers.push(resolve);
      });
      original.headers.Authorization = `Bearer ${token}`;
      original._retry = true;
      return api(original);
    }

    try {
      isRefreshing = true;
      const { data } = await axios.post<{ access_token: string; refresh_token?: string }>(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      setAuthTokens(data);
      await clearVisualCacheOnTokenRefresh();
      refreshSubscribers.forEach((cb) => cb(data.access_token));
      refreshSubscribers = [];
      original._retry = true;
      original.headers.Authorization = `Bearer ${accessToken}`;
      return api(original);
    } catch (refreshError) {
      refreshSubscribers = [];
      clearAuthTokens();
      throw refreshError;
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
  daily_change_percent?: number;
  daily_change_value?: number;
  asset?: string;
  price_status?: string;
  position_qty?: number;
  avg_entry_price?: number;
  timeframe?: string;
  ma_short_period?: number;
  ma_long_period?: number;
  chart: Array<{ time: string; open: number; high: number; low: number; close: number }>;
  ma_short_series?: Array<{ time: string; value: number }>;
  ma_long_series?: Array<{ time: string; value: number }>;
};

export type StrategyConfig = {
  id?: string;
  asset: string;
  timeframe: string;
  ma_short_period: number;
  ma_long_period: number;
};

export type AssetUniverse = {
  b3: string[];
  crypto: string[];
  all: string[];
};

export type BacktestData = {
  period_label: string;
  metrics: {
    total_return: number;
    win_rate: number;
    max_drawdown: number;
    sharpe_ratio: number;
    insight_summary?: string;
    insight_tone?: 'success' | 'warning' | 'danger' | 'neutral';
  };
  equity_curve: number[];
  equity_dates?: string[];
  price_chart?: Array<{ time: string; open: number; high: number; low: number; close: number }>;
  ma_short_series?: Array<{ time: string; value: number }>;
  ma_long_series?: Array<{ time: string; value: number }>;
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
  simulated_balance: number;
};

export type PaperState = {
  balance: number;
  focus_asset: string;
  current_price: number;
  price_status?: string;
  floating_pnl: number;
  floating_pnl_percent?: number;
  invested_capital?: number;
  open_position_asset?: string;
  open_position_qty: number;
  avg_entry_price: number;
  insight_title?: string;
  insight_message?: string;
  insight_tone?: 'success' | 'warning' | 'danger' | 'neutral';
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

export type PaperOrderRow = {
  id: number;
  side: 'buy' | 'sell';
  asset: string;
  price: number;
  quantity: number;
  status: string;
  created_at: string;
};

export async function fetchDashboard(includeChart = true) {
  const { data } = await api.get<DashboardData>(`/dashboard?include_chart=${includeChart ? 'true' : 'false'}`);
  return data;
}

export async function fetchDashboardLite() {
  return fetchDashboard(false);
}

export async function fetchStrategy() {
  const { data } = await api.get<StrategyConfig>('/strategy/config');
  return data;
}

export async function fetchAssetUniverse() {
  const { data } = await api.get<AssetUniverse>('/strategy/assets');
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

export async function runBacktest(period_label: '1mo' | '6mo' | '1y' = '6mo', asset?: string) {
  const { data } = await api.post<BacktestData>('/backtest/run', { period_label, asset });
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
  simulated_balance?: number;
}) {
  const { data } = await api.put<SettingsData>('/settings', payload);
  return data;
}

export async function testConnection() {
  const { data } = await api.post<{ ok: boolean; message: string }>('/settings/test-connection');
  return data;
}

export async function fetchPaperState(asset?: string) {
  const suffix = asset ? `?asset=${encodeURIComponent(asset)}` : '';
  const { data } = await api.get<PaperState>(`/paper/state${suffix}`);
  return data;
}

export async function fetchRecentPaperOrders(limit = 25) {
  const { data } = await api.get<PaperOrderRow[]>(`/paper/orders/recent?limit=${encodeURIComponent(String(limit))}`);
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

export async function paperClosePosition() {
  const { data } = await api.post('/paper/close');
  return data;
}

export async function paperResetWallet(initialBalance?: number) {
  const suffix = initialBalance && initialBalance > 0 ? `?initial_balance=${encodeURIComponent(String(initialBalance))}` : '';
  const { data } = await api.post<PaperState>(`/paper/reset${suffix}`);
  return data;
}
