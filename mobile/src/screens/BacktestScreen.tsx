import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Dimensions, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { LineChart } from 'react-native-chart-kit';
import { fetchAssetUniverse, fetchBacktest, BacktestData, runBacktest } from '../services/api';
import { onConfigChanged } from '../services/events';
import { useAppTheme } from '../theme';

const screenWidth = Dimensions.get('window').width;

function sampleSeries(points: number[], maxPoints = 100): number[] {
  if (points.length <= maxPoints) return points;
  const step = (points.length - 1) / (maxPoints - 1);
  const sampled: number[] = [];
  for (let i = 0; i < maxPoints; i += 1) {
    sampled.push(points[Math.round(i * step)]);
  }
  return sampled;
}

function sampleLabels(points: string[], maxPoints = 100): string[] {
  if (points.length <= maxPoints) return points;
  const step = (points.length - 1) / (maxPoints - 1);
  const sampled: string[] = [];
  for (let i = 0; i < maxPoints; i += 1) {
    sampled.push(points[Math.round(i * step)]);
  }
  return sampled;
}

function buildSparseLabels(points: string[], targetLen: number): string[] {
  if (targetLen <= 0) return [];
  const labels = Array.from({ length: targetLen }, () => '');
  if (!points.length) return labels;

  const sampled = sampleLabels(points, targetLen);
  const last = targetLen - 1;
  const marks = new Set([0, Math.round(last * 0.25), Math.round(last * 0.5), Math.round(last * 0.75), last]);

  marks.forEach((idx) => {
    labels[idx] = formatDateLabel(sampled[idx]);
  });

  return labels;
}

function sanitizeSeries(points: number[]): number[] {
  let lastValid = 0;
  const cleaned: number[] = [];
  for (const p of points) {
    const v = Number(p);
    if (Number.isFinite(v) && v > 0) {
      lastValid = v;
      cleaned.push(v);
    } else if (lastValid > 0) {
      cleaned.push(lastValid);
    }
  }
  return cleaned;
}

function formatDateLabel(value?: string) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return `${dd}/${mm}`;
}

export function BacktestScreen() {
  const { colors, darkMode } = useAppTheme();
  const [data, setData] = useState<BacktestData | null>(null);
  const [asset, setAsset] = useState('PETR4');
  const [period, setPeriod] = useState<'1 Month' | '6 Months' | '1 Year'>('6 Months');
  const [running, setRunning] = useState(false);
  const [assets, setAssets] = useState<string[]>(['PETR4', 'BTC', 'ETH']);

  const styles = useMemo(() => createStyles(colors), [colors]);

  useEffect(() => {
    (async () => {
      const [res, universe] = await Promise.all([fetchBacktest(), fetchAssetUniverse()]);
      setData(res);
      if (universe.all.length > 0) setAssets(universe.all);
    })();
  }, []);

  useEffect(() => {
    const off = onConfigChanged(() => {
      (async () => {
        const res = await fetchBacktest();
        setData(res);
      })();
    });
    return off;
  }, []);

  const onRunBacktest = async () => {
    setRunning(true);
    try {
      const res = await runBacktest(period, asset);
      setData(res);
    } catch (e: any) {
      Alert.alert('Backtest', e?.response?.data?.detail ?? 'Falha ao executar backtest.');
    } finally {
      setRunning(false);
    }
  };

  const sampledCurve = useMemo(() => sanitizeSeries(sampleSeries(data?.equity_curve ?? [])), [data?.equity_curve]);
  const sampledDates = useMemo(() => buildSparseLabels(data?.equity_dates ?? [], sampledCurve.length), [data?.equity_dates, sampledCurve.length]);
  const isCrypto = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'AVAX', 'DOT'].includes(asset.toUpperCase());
  const currency = isCrypto ? 'USD' : 'BRL';
  const yAxisLabel = currency === 'USD' ? 'US$ ' : 'R$ ';

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
      <View style={styles.filterWrap}>
        <Text style={styles.filterLabel}>Ativo</Text>
        <View style={styles.pickerWrap}>
          <Picker selectedValue={asset} onValueChange={setAsset} dropdownIconColor={colors.text} style={styles.picker}>
            {assets.map((symbol) => (
              <Picker.Item key={symbol} label={symbol} value={symbol} />
            ))}
          </Picker>
        </View>
        <Text style={styles.filterLabel}>Período</Text>
        <View style={styles.pickerWrap}>
          <Picker selectedValue={period} onValueChange={setPeriod} dropdownIconColor={colors.text} style={styles.picker}>
            <Picker.Item label="1 mês" value="1 Month" />
            <Picker.Item label="6 meses" value="6 Months" />
            <Picker.Item label="1 ano" value="1 Year" />
          </Picker>
        </View>
      </View>
      <Pressable style={[styles.runBtn, running && styles.runBtnDisabled]} onPress={() => void onRunBacktest()} disabled={running}>
        <Text style={styles.runBtnText}>{running ? 'Rodando backtest...' : 'Rodar Backtest'}</Text>
      </Pressable>
      {sampledCurve.length > 0 ? (
        <LineChart
          data={{ labels: sampledDates, datasets: [{ data: sampledCurve }] }}
          width={screenWidth - 24}
          height={220}
          yAxisLabel={yAxisLabel}
          withDots={false}
          withInnerLines
          chartConfig={{
            backgroundGradientFrom: darkMode ? '#0b0f1a' : '#ffffff',
            backgroundGradientTo: darkMode ? '#0b0f1a' : '#ffffff',
            color: () => '#60a5fa',
            labelColor: () => colors.muted,
            decimalPlaces: 0,
          }}
          bezier
          style={styles.chart}
        />
      ) : (
        <View style={styles.chartUnavailable}>
          <Text style={styles.emptyChartText}>Gráfico indisponível para este ativo no momento</Text>
        </View>
      )}

      <View style={styles.metricsRow}>
        <MetricCard label="Retorno Total" value={`${data.metrics.total_return.toFixed(2)}%`} success colors={colors} styles={styles} />
        <MetricCard label="Win Rate" value={`${data.metrics.win_rate.toFixed(2)}%`} success colors={colors} styles={styles} />
      </View>
      <View style={styles.metricsRow}>
        <MetricCard label="Max Drawdown" value={`${data.metrics.max_drawdown.toFixed(2)}%`} danger colors={colors} styles={styles} />
        <MetricCard label="Sharpe" value={data.metrics.sharpe_ratio.toFixed(2)} success colors={colors} styles={styles} />
      </View>
    </ScrollView>
  );
}

function MetricCard({
  label,
  value,
  success,
  danger,
  colors,
  styles,
}: {
  label: string;
  value: string;
  success?: boolean;
  danger?: boolean;
  colors: ReturnType<typeof useAppTheme>['colors'];
  styles: ReturnType<typeof createStyles>;
}) {
  const color = success ? colors.success : danger ? colors.danger : colors.text;
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, { color }]}>{value}</Text>
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) =>
  StyleSheet.create({
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
    runBtnDisabled: { opacity: 0.65 },
    runBtnText: { color: '#fff', fontWeight: '700' },
    filterWrap: { backgroundColor: colors.card, borderRadius: 12, padding: 10, marginBottom: 10 },
    filterLabel: { color: colors.text, fontWeight: '600', marginBottom: 4, marginTop: 4 },
    pickerWrap: { backgroundColor: colors.cardSoft, borderRadius: 10, borderWidth: 1, borderColor: colors.border },
    picker: { color: colors.text },
    chart: { borderRadius: 12 },
    chartUnavailable: {
      backgroundColor: colors.card,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: colors.border,
      minHeight: 120,
      alignItems: 'center',
      justifyContent: 'center',
    },
    emptyChartText: { color: colors.muted },
    metricsRow: { flexDirection: 'row', gap: 10, marginTop: 10 },
    metricCard: { flex: 1, backgroundColor: colors.card, borderRadius: 12, padding: 12 },
    metricLabel: { color: colors.muted, fontSize: 13 },
    metricValue: { color: colors.text, fontSize: 22, fontWeight: '700', marginTop: 6 },
  });
