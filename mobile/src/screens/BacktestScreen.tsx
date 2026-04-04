import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Dimensions, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { fetchBacktest, BacktestData, runBacktest } from '../services/api';
import { colors } from '../theme';

const width = Dimensions.get('window').width - 24;

export function BacktestScreen() {
  const [data, setData] = useState<BacktestData | null>(null);

  useEffect(() => {
    (async () => {
      const res = await fetchBacktest();
      setData(res);
    })();
  }, []);

  const onRunBacktest = async () => {
    const res = await runBacktest('6 Months');
    setData(res);
  };

  if (!data) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Período: {data.period_label}</Text>
      <TouchableOpacity style={styles.runBtn} onPress={onRunBacktest}>
        <Text style={styles.runBtnText}>Rodar Backtest (Pandas)</Text>
      </TouchableOpacity>
      <LineChart
        data={{ labels: data.equity_curve.map(() => ''), datasets: [{ data: data.equity_curve }] }}
        width={width}
        height={220}
        withDots
        withInnerLines
        chartConfig={{
          backgroundGradientFrom: '#0b0f1a',
          backgroundGradientTo: '#0b0f1a',
          color: () => '#60a5fa',
          labelColor: () => colors.muted,
        }}
        bezier
        style={styles.chart}
      />

      <View style={styles.metricsRow}>
        <MetricCard label="Retorno Total" value={`${data.metrics.total_return.toFixed(2)}%`} success />
        <MetricCard label="Win Rate" value={`${data.metrics.win_rate.toFixed(2)}%`} success />
      </View>
      <View style={styles.metricsRow}>
        <MetricCard label="Max Drawdown" value={`${data.metrics.max_drawdown.toFixed(2)}%`} danger />
        <MetricCard label="Sharpe" value={data.metrics.sharpe_ratio.toFixed(2)} success />
      </View>
    </ScrollView>
  );
}

function MetricCard({
  label,
  value,
  success,
  danger,
}: {
  label: string;
  value: string;
  success?: boolean;
  danger?: boolean;
}) {
  const color = success ? colors.success : danger ? colors.danger : colors.text;
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, { color }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: 12 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  title: { color: colors.text, marginBottom: 8, fontSize: 16 },
  runBtn: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  runBtnText: { color: '#fff', fontWeight: '700' },
  chart: { borderRadius: 12 },
  metricsRow: { flexDirection: 'row', gap: 10, marginTop: 10 },
  metricCard: { flex: 1, backgroundColor: colors.card, borderRadius: 12, padding: 12 },
  metricLabel: { color: colors.muted, fontSize: 13 },
  metricValue: { color: colors.text, fontSize: 22, fontWeight: '700', marginTop: 6 },
});
