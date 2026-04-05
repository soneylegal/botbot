import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useStrategyContext } from '../context/StrategyContext';
import { useAppTheme } from '../theme';
import { onConfigChanged } from '../services/events';
import { DashboardData, fetchDashboard, fetchDashboardLite, getMarketWsUrl } from '../services/api';
import { TradingViewCandles } from '../components/TradingViewCandles';

const CRYPTO_ASSETS = new Set(['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'AVAX', 'DOT']);

export function DashboardScreen() {
  const { colors, darkMode } = useAppTheme();
  const [data, setData] = useState<DashboardData | null>(null);
  const [lastGoodChart, setLastGoodChart] = useState<DashboardData['chart']>([]);
  const [lastGoodShort, setLastGoodShort] = useState<NonNullable<DashboardData['ma_short_series']>>([]);
  const [lastGoodLong, setLastGoodLong] = useState<NonNullable<DashboardData['ma_long_series']>>([]);
  const [loading, setLoading] = useState(true);
  const [updatePaused, setUpdatePaused] = useState(false);
  const [wsNonce, setWsNonce] = useState(0);
  const { strategy } = useStrategyContext();
  const styles = useMemo(() => createStyles(colors), [colors]);
  const lastGoodChartRef = useRef<DashboardData['chart']>([]);
  const lastGoodShortRef = useRef<NonNullable<DashboardData['ma_short_series']>>([]);
  const lastGoodLongRef = useRef<NonNullable<DashboardData['ma_long_series']>>([]);

  const cacheLastGood = useCallback(
    (
      chart: DashboardData['chart'],
      shortSeries: NonNullable<DashboardData['ma_short_series']>,
      longSeries: NonNullable<DashboardData['ma_long_series']>
    ) => {
      lastGoodChartRef.current = chart;
      lastGoodShortRef.current = shortSeries;
      lastGoodLongRef.current = longSeries;
      setLastGoodChart(chart);
      setLastGoodShort(shortSeries);
      setLastGoodLong(longSeries);
    },
    []
  );

  const loadChartData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchDashboard(true);
      const hasIncomingChart = Array.isArray(res.chart) && res.chart.length > 0;
      const safeChart = hasIncomingChart ? res.chart : lastGoodChartRef.current;
      const safeShort = (res.ma_short_series?.length ? res.ma_short_series : lastGoodShortRef.current) ?? [];
      const safeLong = (res.ma_long_series?.length ? res.ma_long_series : lastGoodLongRef.current) ?? [];

      setData({ ...res, chart: safeChart, ma_short_series: safeShort, ma_long_series: safeLong });

      if (hasIncomingChart) {
        cacheLastGood(res.chart, res.ma_short_series ?? [], res.ma_long_series ?? []);
        setUpdatePaused(false);
      } else if (lastGoodChartRef.current.length > 0) {
        setUpdatePaused(true);
      }
    } catch {
      if (lastGoodChartRef.current.length > 0) {
        setUpdatePaused(true);
      }
    } finally {
      setLoading(false);
    }
  }, [cacheLastGood]);

  const pollPriceSnapshot = useCallback(async () => {
    try {
      const res = await fetchDashboardLite();
      setData((prev) => {
        if (!prev) {
          return {
            ...res,
            chart: lastGoodChartRef.current,
            ma_short_series: lastGoodShortRef.current,
            ma_long_series: lastGoodLongRef.current,
          };
        }

        const currentAsset = (prev.asset ?? '').toUpperCase();
        const incomingAsset = (res.asset ?? '').toUpperCase();
        if (incomingAsset && currentAsset && incomingAsset !== currentAsset) {
          setWsNonce((v) => v + 1);
          void loadChartData();
        }

        return {
          ...prev,
          ...res,
          chart: prev.chart?.length ? prev.chart : lastGoodChartRef.current,
          ma_short_series: prev.ma_short_series?.length ? prev.ma_short_series : lastGoodShortRef.current,
          ma_long_series: prev.ma_long_series?.length ? prev.ma_long_series : lastGoodLongRef.current,
        };
      });
    } catch {
      if (lastGoodChartRef.current.length > 0) {
        setUpdatePaused(true);
      }
    }
  }, [loadChartData]);

  useEffect(() => {
    void loadChartData();
  }, [loadChartData]);

  useEffect(() => {
    if (!strategy?.asset) return;
    setWsNonce((v) => v + 1);
    void loadChartData();
  }, [loadChartData, strategy?.asset, strategy?.timeframe, strategy?.ma_short_period, strategy?.ma_long_period]);

  useEffect(() => {
    const timer = setInterval(() => {
      void pollPriceSnapshot();
    }, 10000);
    return () => clearInterval(timer);
  }, [pollPriceSnapshot]);

  useEffect(() => {
    const off = onConfigChanged(() => {
      setWsNonce((v) => v + 1);
      void loadChartData();
    });
    return off;
  }, [loadChartData]);

  useEffect(() => {
    const asset = data?.asset;
    if (!asset) return;

    const ws = new WebSocket(getMarketWsUrl(asset));
    const heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 10000);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setData((prev) => {
          if (!prev) return prev;

          const currentChart = prev.chart?.length ? prev.chart : lastGoodChartRef.current;
          if (!currentChart.length) return prev;

          const raw = Number(payload.price);
          const safePrice = Number.isFinite(raw) && raw > 0 ? raw : Number(currentChart[currentChart.length - 1]?.close ?? 0);
          if (!safePrice || safePrice <= 0) return prev;

          const rawTime = String(payload.tick_at || new Date().toISOString());
          const prevLast = currentChart[currentChart.length - 1];
          const nextLast = {
            ...prevLast,
            time: rawTime,
            high: Math.max(Number(prevLast.high), safePrice),
            low: Math.min(Number(prevLast.low), safePrice),
            close: safePrice,
          };
          const nextChart = [...currentChart.slice(0, -1), nextLast].slice(-180);
          cacheLastGood(nextChart, lastGoodShortRef.current, lastGoodLongRef.current);
          return { ...prev, chart: nextChart };
        });
      } catch {
        // ignore malformed payload
      }
    };

    return () => {
      clearInterval(heartbeat);
      ws.close();
    };
  }, [cacheLastGood, data?.asset, wsNonce]);

  const chartToRender = data?.chart?.length ? data.chart : lastGoodChart;
  const shortSeries = (data?.ma_short_series?.length ? data.ma_short_series : lastGoodShort) ?? [];
  const longSeries = (data?.ma_long_series?.length ? data.ma_long_series : lastGoodLong) ?? [];
  const canRenderChart = chartToRender.length > 0;

  const asset = (data?.asset ?? 'PETR4').toUpperCase();
  const currency = CRYPTO_ASSETS.has(asset) ? 'USD' : 'BRL';
  const moneyFmt = useMemo(
    () => new Intl.NumberFormat('pt-BR', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    [currency]
  );
  const formatSignedMoney = (value: number) => `${value > 0 ? '+' : ''}${moneyFmt.format(value)}`;

  const statusMessage = data?.asset
    ? `Monitorando ${data.asset} no mercado para possíveis entradas`
    : 'Monitorando ativo no mercado para possíveis entradas';

  if (loading && !data) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadChartData} tintColor={colors.primary} />}
    >
      <Text style={styles.title}>Ativo: {data?.asset ?? '-'}</Text>
      <Text style={styles.subtitle}>O Bot está monitorando este gráfico para cruzamento de médias.</Text>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Configuração Ativa do Bot</Text>
        <Text style={styles.row}>Ativo: {data?.asset ?? '-'}</Text>
        <Text style={styles.row}>Timeframe: {data?.timeframe ?? '-'}</Text>
        <Text style={styles.row}>MA Curta: {data?.ma_short_period ?? '-'}</Text>
        <Text style={styles.row}>MA Longa: {data?.ma_long_period ?? '-'}</Text>
      </View>

      {canRenderChart ? (
        <TradingViewCandles
          candles={chartToRender}
          maShort={shortSeries}
          maLong={longSeries}
          darkMode={darkMode}
          height={300}
        />
      ) : (
        <Text style={{ textAlign: 'center', marginVertical: 20, color: colors.muted }}>
          Gráfico temporariamente indisponível.
        </Text>
      )}

      {updatePaused ? <Text style={styles.paused}>Atualização pausada</Text> : null}

      <View style={styles.card}>
        <Text style={styles.row}>Bot Status: <Text style={styles.success}>{statusMessage}</Text></Text>
        <Text style={styles.subtle}>Fonte de preço: {data?.price_status ?? 'Preço indisponível'}</Text>
        <Text style={styles.row}>
          P/L Diário:{' '}
          <Text
            style={
              Number(data?.daily_pnl) > 0
                ? styles.success
                : Number(data?.daily_pnl) < 0
                ? styles.error
                : styles.row
            }
          >
            {formatSignedMoney(Number(data?.daily_pnl ?? 0))}
          </Text>
        </Text>
      </View>
    </ScrollView>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 12 },
    content: { flexGrow: 1, paddingBottom: 40 },
    center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
    title: { color: colors.text, fontSize: 16, marginBottom: 10 },
    subtitle: { color: colors.muted, fontSize: 12, marginBottom: 10 },
    card: { marginTop: 16, backgroundColor: colors.card, borderRadius: 12, padding: 14 },
    row: { color: colors.text, fontSize: 16, marginBottom: 6 },
    subtle: { color: colors.muted, fontSize: 12, marginBottom: 8 },
    success: { color: colors.success },
    error: { color: colors.danger },
    sectionTitle: { color: colors.text, fontWeight: '700', marginBottom: 8 },
    paused: { color: colors.warning, fontSize: 12, marginTop: 8 },
  });
