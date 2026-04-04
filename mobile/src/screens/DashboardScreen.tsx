import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Dimensions, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { colors } from '../theme';
import { DashboardData, fetchDashboard, getMarketWsUrl } from '../services/api';

const width = Dimensions.get('window').width - 24;

export function DashboardScreen() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const res = await fetchDashboard();
      setData(res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 8000);
    return () => clearInterval(timer);
  }, []);

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
          const nextChart = [...prev.chart, { t: payload.tick_at, p: Number(payload.price) }].slice(-80);
          return { ...prev, asset: payload.asset || prev.asset, chart: nextChart };
        });
      } catch {
        // ignore malformed payload
      }
    };

    return () => {
      clearInterval(heartbeat);
      ws.close();
    };
  }, [data?.asset]);

  if (loading && !data) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  const prices = data?.chart?.map((p) => p.p) ?? [0];

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={colors.primary} />}
    >
      <Text style={styles.title}>Ativo: {data?.asset ?? '-'}</Text>

      <LineChart
        data={{ labels: prices.map(() => ''), datasets: [{ data: prices }] }}
        width={width}
        height={240}
        yAxisLabel="R$ "
        withDots={false}
        withInnerLines
        chartConfig={{
          backgroundGradientFrom: '#0b0f1a',
          backgroundGradientTo: '#0b0f1a',
          color: () => colors.primary,
          labelColor: () => colors.muted,
          decimalPlaces: 2,
        }}
        bezier
        style={styles.chart}
      />

      <View style={styles.card}>
        <Text style={styles.row}>Bot Status: <Text style={styles.success}>{data?.status}</Text></Text>
        <Text style={styles.row}>
          P/L Diário:{' '}
          <Text style={Number(data?.daily_pnl) >= 0 ? styles.success : styles.error}>
            {Number(data?.daily_pnl).toFixed(2)}
          </Text>
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: 12 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  title: { color: colors.text, fontSize: 16, marginBottom: 10 },
  chart: { borderRadius: 12 },
  card: { marginTop: 16, backgroundColor: colors.card, borderRadius: 12, padding: 14 },
  row: { color: colors.text, fontSize: 16, marginBottom: 6 },
  success: { color: colors.success },
  error: { color: colors.danger },
});
