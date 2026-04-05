import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Dimensions, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { LineChart } from 'react-native-chart-kit';
import { useAppTheme } from '../theme';
import { onConfigChanged } from '../services/events';
import { DashboardData, fetchDashboard, getMarketWsUrl } from '../services/api';

const screenWidth = Dimensions.get('window').width;
const CRYPTO_ASSETS = new Set(['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'AVAX', 'DOT']);

function normalizeChart(points: Array<{ t: string; p: number }>) {
  let lastValid = 0;
  const normalized: Array<{ t: string; p: number }> = [];
  for (const point of points) {
    const value = Number(point.p);
    if (Number.isFinite(value) && value > 0) {
      lastValid = value;
      normalized.push({ ...point, p: value });
    } else if (lastValid > 0) {
      normalized.push({ ...point, p: lastValid });
    }
  }
  return normalized;
}

function hasVolatility(values: number[]) {
  if (values.length < 2) return false;
  const first = values[0];
  return values.some((v) => v !== first);
}

export function DashboardScreen() {
  const { colors, darkMode } = useAppTheme();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [wsNonce, setWsNonce] = useState(0);
  const styles = useMemo(() => createStyles(colors), [colors]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchDashboard();
      setData(res);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      let active = true;

      setData((prev) => (prev ? { ...prev, chart: [] } : prev));

      const run = async () => {
        if (!active) return;
        await load();
      };

      void run();
      const timer = setInterval(() => {
        void run();
      }, 8000);

      return () => {
        active = false;
        clearInterval(timer);
      };
    }, [load])
  );

  useEffect(() => {
    const off = onConfigChanged(() => {
      setData((prev) => (prev ? { ...prev, asset: undefined, chart: [] } : prev));
      setWsNonce((v) => v + 1);
      void load();
    });
    return off;
  }, [load]);

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
          const raw = Number(payload.price);
          const safePrice = Number.isFinite(raw) && raw > 0 ? raw : Number(prev.chart[prev.chart.length - 1]?.p ?? 0);
          const nextChart = [...prev.chart, { t: payload.tick_at, p: safePrice }].slice(-80);
          const qty = Number(prev.position_qty ?? 0);
          const avg = Number(prev.avg_entry_price ?? 0);
          const nextPnl = qty > 0 && avg > 0 ? (safePrice - avg) * qty : prev.daily_pnl;
          return { ...prev, chart: nextChart, daily_pnl: nextPnl };
        });
      } catch {
        // ignore malformed payload
      }
    };

    return () => {
      clearInterval(heartbeat);
      ws.close();
    };
  }, [data?.asset, wsNonce]);

  const normalized = normalizeChart(data?.chart ?? []);
  const prices = normalized.map((p) => p.p);
  const canRenderChart = hasVolatility(prices);

  const chartBackground = darkMode ? '#0b0f1a' : '#ffffff';
  const asset = (data?.asset ?? 'PETR4').toUpperCase();
  const currency = CRYPTO_ASSETS.has(asset) ? 'USD' : 'BRL';
  const moneyFmt = useMemo(
    () => new Intl.NumberFormat('pt-BR', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    [currency]
  );
  const formatSignedMoney = (value: number) => `${value > 0 ? '+' : ''}${moneyFmt.format(value)}`;
  const yAxisLabel = currency === 'USD' ? 'US$ ' : 'R$ ';

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
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={colors.primary} />}
    >
      <Text style={styles.title}>Ativo: {data?.asset ?? '-'}</Text>
      <Text style={styles.subtitle}>O Bot está monitorando este gráfico para cruzamento de médias.</Text>

      {canRenderChart ? (
        <LineChart
          data={{
            labels: prices.map(() => ''),
            datasets: [{ data: prices }],
          }}
          width={screenWidth - 24}
          height={240}
          yAxisLabel={yAxisLabel}
          withDots={false}
          withInnerLines
          segments={4}
          chartConfig={{
            backgroundGradientFrom: chartBackground,
            backgroundGradientTo: chartBackground,
            color: () => colors.primary,
            labelColor: () => colors.muted,
            decimalPlaces: 2,
          }}
          bezier
          style={styles.chart}
        />
      ) : (
        <Text style={{ textAlign: 'center', marginVertical: 20, color: colors.muted }}>
          Aguardando volatilidade ou dados do mercado...
        </Text>
      )}

      <View style={styles.card}>
        <Text style={styles.row}>Bot Status: <Text style={styles.success}>{data?.status}</Text></Text>
        <Text style={styles.subtle}>Fonte de preço: {data?.price_status ?? 'Preço em Cache'}</Text>
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
    center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
    title: { color: colors.text, fontSize: 16, marginBottom: 10 },
    subtitle: { color: colors.muted, fontSize: 12, marginBottom: 10 },
    chart: { borderRadius: 12 },
    chartUnavailable: {
      backgroundColor: colors.card,
      borderColor: colors.border,
      borderWidth: 1,
      borderRadius: 12,
      minHeight: 120,
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 4,
    },
    card: { marginTop: 16, backgroundColor: colors.card, borderRadius: 12, padding: 14 },
    row: { color: colors.text, fontSize: 16, marginBottom: 6 },
    subtle: { color: colors.muted, fontSize: 12, marginBottom: 8 },
    success: { color: colors.success },
    error: { color: colors.danger },
  });
