import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { useStrategyContext } from '../context/StrategyContext';
import { fetchAssetUniverse, fetchBacktest, BacktestData, runBacktest } from '../services/api';
import { onConfigChanged } from '../services/events';
import { useAppTheme } from '../theme';
import { TradingViewCandles } from '../components/TradingViewCandles';

type PeriodCode = '1mo' | '6mo' | '1y';

export function BacktestScreen() {
  const { colors, darkMode } = useAppTheme();
  const [data, setData] = useState<BacktestData | null>(null);
  const [asset, setAsset] = useState('PETR4');
  const [period, setPeriod] = useState<PeriodCode>('6mo');
  const [running, setRunning] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [chartInteracting, setChartInteracting] = useState(false);
  const [assets, setAssets] = useState<string[]>(['PETR4', 'BTC', 'ETH']);
  const { strategy } = useStrategyContext();

  const styles = useMemo(() => createStyles(colors), [colors]);

  useEffect(() => {
    (async () => {
      try {
        setLoadingData(true);
        const [res, universe] = await Promise.all([fetchBacktest(), fetchAssetUniverse()]);
        setData(res);
        if (universe.all.length > 0) setAssets(universe.all);
      } finally {
        setLoadingData(false);
      }
    })();
  }, []);

  useEffect(() => {
    const off = onConfigChanged(() => {
      (async () => {
        try {
          setLoadingData(true);
          const res = await fetchBacktest();
          setData(res);
        } finally {
          setLoadingData(false);
        }
      })();
    });
    return off;
  }, []);

  useEffect(() => {
    const strategyAsset = strategy?.asset?.toUpperCase?.();
    if (!strategyAsset || strategyAsset === asset) return;
    setAsset(strategyAsset);
  }, [asset, strategy?.asset]);

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

  const canRenderChart = (data?.price_chart?.length ?? 0) > 0;
  const hasCurve = (data?.equity_curve?.length ?? 0) > 0;
  const isCrypto = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'AVAX', 'DOT'].includes(asset.toUpperCase());
  const currency = isCrypto ? 'USD' : 'BRL';
  const moneyFmt = useMemo(
    () => new Intl.NumberFormat('pt-BR', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    [currency]
  );
  const insightTone = data?.metrics?.insight_tone ?? 'neutral';
  const insightStyle =
    insightTone === 'success'
      ? styles.insightSuccess
      : insightTone === 'danger'
      ? styles.insightDanger
      : insightTone === 'warning'
      ? styles.insightWarning
      : styles.insightNeutral;

  if (!data || loadingData) {
    return (
      <View style={[styles.center, { flex: 1 }]}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView 
        style={{ flex: 1 }} 
        contentContainerStyle={{ paddingBottom: 40, flexGrow: 1, padding: 12 }}
        showsVerticalScrollIndicator={false}
        scrollEnabled={!chartInteracting}
      >
        <Text style={styles.explain}>
          Simulação do cruzamento de médias (MA Curta vs MA Longa) no histórico do ativo para avaliar a rentabilidade da estratégia.
        </Text>
        <Text style={styles.axisHint}>Eixo Y = Evolução do Capital Simulado | Eixo X = Linha do Tempo</Text>
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
              <Picker.Item label="1 mês" value="1mo" />
              <Picker.Item label="6 meses" value="6mo" />
              <Picker.Item label="1 ano" value="1y" />
            </Picker>
          </View>
        </View>
        <Pressable style={[styles.runBtn, running && styles.runBtnDisabled]} onPress={() => void onRunBacktest()} disabled={running}>
          {running ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.runBtnText}>Rodar Backtest</Text>}
        </Pressable>
        {canRenderChart ? (
          <TradingViewCandles
            candles={data?.price_chart ?? []}
            maShort={data?.ma_short_series ?? []}
            maLong={data?.ma_long_series ?? []}
            darkMode={darkMode}
            height={300}
            onInteractionChange={setChartInteracting}
          />
        ) : (
          <Text style={{ textAlign: 'center', marginVertical: 20, color: colors.muted }}>
            Gráfico temporariamente indisponível.
          </Text>
        )}

        {running ? (
          <View style={styles.loadingInline}>
            <ActivityIndicator color={colors.primary} size="small" />
            <Text style={styles.loadingText}>Processando backtest…</Text>
          </View>
        ) : null}

        <Text style={styles.subtleLine}>
          Capital final: {hasCurve ? moneyFmt.format(Number(data.equity_curve?.at(-1) ?? 0)) : 'Dados não disponíveis no momento'}
        </Text>

        <View style={styles.metricsRow}>
          <MetricCard label="Retorno Total" value={`${data.metrics.total_return.toFixed(2)}%`} success colors={colors} styles={styles} />
          <MetricCard label="Win Rate" value={`${data.metrics.win_rate.toFixed(2)}%`} success colors={colors} styles={styles} />
        </View>
        <View style={styles.metricsRow}>
          <MetricCard label="Max Drawdown" value={`${data.metrics.max_drawdown.toFixed(2)}%`} danger colors={colors} styles={styles} />
          <MetricCard label="Sharpe" value={data.metrics.sharpe_ratio.toFixed(2)} success colors={colors} styles={styles} />
        </View>

        {data.metrics.insight_summary ? (
          <View style={[styles.insightBox, insightStyle]}>
            <Text style={styles.insightText}>{data.metrics.insight_summary}</Text>
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}

function MetricCard({ label, value, success, danger, colors, styles }: {
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
    metricsRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
    metricCard: { width: '48%', backgroundColor: colors.card, padding: 12, borderRadius: 10, borderWidth: 1, borderColor: colors.border },
    metricLabel: { color: colors.text, fontSize: 12, marginBottom: 4 },
    metricValue: { fontWeight: 'bold', fontSize: 16 },
    explain: { color: colors.muted, marginBottom: 8, lineHeight: 20 },
    axisHint: { color: colors.muted, marginBottom: 10, fontSize: 12 },
    subtleLine: { color: colors.muted, marginTop: 10 },
    insightBox: { backgroundColor: colors.cardSoft, padding: 12, borderRadius: 10, marginTop: 10, borderWidth: 1, borderColor: colors.primary + '40' },
    insightText: { color: colors.text, fontSize: 14, lineHeight: 22 },
    insightSuccess: { borderColor: colors.success, backgroundColor: colors.success + '20' },
    insightDanger: { borderColor: colors.danger, backgroundColor: colors.danger + '20' },
    insightWarning: { borderColor: colors.warning, backgroundColor: colors.warning + '20' },
    insightNeutral: { borderColor: colors.primary + '40', backgroundColor: colors.cardSoft },
    loadingInline: { marginTop: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
    loadingText: { color: colors.muted, fontSize: 12, marginLeft: 8 },
  });
