import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { useStrategyContext } from '../context/StrategyContext';
import {
  fetchAssetUniverse,
  fetchPaperState,
  fetchRecentPaperOrders,
  paperBuy,
  paperClosePosition,
  paperResetWallet,
  paperSell,
  PaperOrderRow,
  PaperState,
} from '../services/api';
import { onConfigChanged } from '../services/events';
import { useAppTheme } from '../theme';

const ASSET_OPTIONS = ['PETR4', 'VALE3', 'ITUB4', 'BTC', 'ETH'];
const CRYPTO_ASSETS = new Set(['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'AVAX', 'DOT']);

export function PaperTradingScreen() {
  const { colors, darkMode } = useAppTheme();
  const [state, setState] = useState<PaperState | null>(null);
  const [orders, setOrders] = useState<PaperOrderRow[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [assetOptions, setAssetOptions] = useState<string[]>(ASSET_OPTIONS);
  const [orderQty, setOrderQty] = useState('1');
  const [showManual, setShowManual] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const { strategy } = useStrategyContext();
  const refreshLock = useRef(false);

  const asset = (strategy?.asset || state?.focus_asset || 'PETR4').toUpperCase();

  const styles = useMemo(() => createStyles(colors, darkMode), [colors, darkMode]);
  const upperAsset = asset.toUpperCase();
  const currency = CRYPTO_ASSETS.has(upperAsset) ? 'USD' : 'BRL';
  const moneyFmt = useMemo(
    () => new Intl.NumberFormat('pt-BR', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    [currency]
  );

  const formatSignedMoney = useCallback((value: number) => `${value > 0 ? '+' : ''}${moneyFmt.format(value)}`, [moneyFmt]);

  const loadState = useCallback(async () => {
    const data = await fetchPaperState();
    setState(data);
  }, []);

  const loadOrders = useCallback(async () => {
    const data = await fetchRecentPaperOrders(25);
    setOrders(data);
  }, []);

  const refreshAll = useCallback(async () => {
    if (refreshLock.current) return;
    refreshLock.current = true;
    try {
      setIsRefreshing(true);
      await Promise.all([loadState(), loadOrders()]);
    } finally {
      refreshLock.current = false;
      setIsRefreshing(false);
    }
  }, [loadOrders, loadState]);

  useEffect(() => {
    (async () => {
      try {
        const universe = await fetchAssetUniverse();
        if (universe.all?.length) setAssetOptions(universe.all);
        await refreshAll();
      } catch {
        await refreshAll();
      } finally {
        setIsLoading(false);
      }
    })();
  }, [refreshAll]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll, strategy?.asset]);

  useEffect(() => {
    const off = onConfigChanged(() => {
      void refreshAll();
    });
    return off;
  }, [refreshAll]);

  useEffect(() => {
    void refreshAll();
    const timer = setInterval(() => {
      void refreshAll();
    }, 10000);
    return () => clearInterval(timer);
  }, [refreshAll]);

  const onBuy = async () => {
    if (submitting) return;
    const qty = Number(orderQty.replace(',', '.'));
    if (!Number.isFinite(qty) || qty <= 0) {
      Alert.alert('Quantidade inválida', 'Informe uma quantidade maior que zero.');
      return;
    }
    setSubmitting(true);
    try {
      const fallback = Number(state?.current_price ?? 0) || Number(state?.avg_entry_price ?? 0) || 0;
      await paperBuy({ asset, price: fallback, quantity: qty });
      await refreshAll();
      Alert.alert('Ordem executada', `BUY ${asset}`);
    } catch (e: any) {
      Alert.alert('Falha na compra', e?.response?.data?.detail ?? 'Não foi possível executar a compra.');
    } finally {
      setSubmitting(false);
    }
  };

  const onSell = async () => {
    if (submitting) return;
    const qty = Number(orderQty.replace(',', '.'));
    if (!Number.isFinite(qty) || qty <= 0) {
      Alert.alert('Quantidade inválida', 'Informe uma quantidade maior que zero.');
      return;
    }
    setSubmitting(true);
    try {
      const fallback = Number(state?.current_price ?? 0) || Number(state?.avg_entry_price ?? 0) || 0;
      await paperSell({ asset, price: fallback, quantity: qty });
      await refreshAll();
      Alert.alert('Ordem executada', `SELL ${asset}`);
    } catch (e: any) {
      Alert.alert('Falha na venda', e?.response?.data?.detail ?? 'Não foi possível executar a venda.');
    } finally {
      setSubmitting(false);
    }
  };

  const onClosePosition = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await paperClosePosition();
      await refreshAll();
      Alert.alert('Posição encerrada', 'Toda a posição aberta foi vendida.');
    } catch (e: any) {
      Alert.alert('Falha ao encerrar', e?.response?.data?.detail ?? 'Não foi possível fechar a posição.');
    } finally {
      setSubmitting(false);
    }
  };

  const onResetWallet = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const next = await paperResetWallet();
      setState(next);
      await loadOrders();
      Alert.alert('Carteira resetada', `Saldo voltou para ${moneyFmt.format(Number(next.balance ?? 0))}.`);
    } catch (e: any) {
      Alert.alert('Falha ao resetar', e?.response?.data?.detail ?? 'Não foi possível resetar a carteira.');
    } finally {
      setSubmitting(false);
    }
  };

  const hasOpenPosition = !!state?.open_position_asset && Number(state?.open_position_qty ?? 0) > 0;

  if (isLoading || !state) {
    return (
      <View style={[styles.container, { alignItems: 'center', justifyContent: 'center' }]}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.badge}>EXTRATO AUTÔNOMO DO BOT</Text>

      {isRefreshing ? (
        <View style={styles.loadingInline}>
          <ActivityIndicator color={colors.primary} size="small" />
          <Text style={styles.loadingText}>Sincronizando ordens e P/L…</Text>
        </View>
      ) : null}

      <View style={styles.ledgerHeader}>
        <Text style={styles.ledgerLine}>Ativo em foco: {asset}</Text>
        <Text style={styles.ledgerLine}>Preço atual: {moneyFmt.format(Number(state?.current_price ?? 0))}</Text>
        <Text style={styles.ledgerLine}>Posição atual: {(state?.open_position_qty ?? 0).toFixed(4)} {state?.open_position_asset ?? '-'}</Text>
        <Text style={styles.ledgerLine}>Preço médio: {moneyFmt.format(Number(state?.avg_entry_price ?? 0))}</Text>
        <Text style={[styles.ledgerPnl, Number(state?.floating_pnl ?? 0) >= 0 ? styles.profit : styles.loss]}>
          P/L Atual: {formatSignedMoney(Number(state?.floating_pnl ?? 0))}
        </Text>
        <Text style={styles.quoteStatus}>Fonte de preço: {state?.price_status ?? 'Indisponível'}</Text>
      </View>

      <Text style={styles.asset}>Ativo para consulta</Text>
      <View style={styles.pickerWrap}>
        <Picker enabled={false} selectedValue={asset} onValueChange={() => {}} dropdownIconColor={colors.text} style={styles.picker}>
          {assetOptions.map((a) => (
            <Picker.Item key={a} label={a} value={a} />
          ))}
        </Picker>
      </View>
      <Text style={styles.assetHint}>Sincronizado automaticamente com a Estratégia Ativa.</Text>

      {hasOpenPosition ? (
        <View style={styles.warnBanner}>
          <Text style={styles.warnBannerText}>
            Posição aberta detectada em {state?.open_position_asset}. O P/L está sendo recalculado automaticamente a cada 10s.
          </Text>
        </View>
      ) : null}

      <Text style={styles.subtitle}>Extrato do Robô</Text>
      {orders.length === 0 ? <Text style={styles.emptyText}>Sem ordens recentes.</Text> : null}
      {orders.map((item) => (
        <View key={String(item.id)} style={styles.orderRow}>
          <Text style={styles.orderMain}>
            {new Date(item.created_at).toLocaleString()} | {item.asset} | {item.side === 'buy' ? 'Compra' : 'Venda'} | {moneyFmt.format(Number(item.price ?? 0))} | Executado por: BOT
          </Text>
        </View>
      ))}

      <Pressable onPress={() => setShowManual((v) => !v)} style={styles.manualToggle}>
        <Text style={styles.manualToggleText}>Modo Intervenção Manual {showManual ? '▼' : '►'}</Text>
      </Pressable>

      {showManual ? (
        <View style={styles.manualBox}>
          <Text style={styles.qtyLabel}>Quantidade da Ordem</Text>
          <TextInput
            value={orderQty}
            onChangeText={setOrderQty}
            keyboardType="numeric"
            placeholder="1"
            placeholderTextColor={colors.muted}
            style={styles.qtyInput}
          />

          <View style={styles.actions}>
            <Pressable
              style={[styles.actionBtn, { backgroundColor: colors.success }, submitting && styles.actionBtnDisabled]}
              onPress={() => void onBuy()}
              disabled={submitting}
            >
              {submitting ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.actionTxt}>BUY</Text>}
            </Pressable>
            <Pressable
              style={[styles.actionBtn, { backgroundColor: colors.danger }, submitting && styles.actionBtnDisabled]}
              onPress={() => void onSell()}
              disabled={submitting}
            >
              {submitting ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.actionTxt}>SELL</Text>}
            </Pressable>
          </View>

          <Pressable style={[styles.closeBtn, submitting && styles.actionBtnDisabled]} onPress={() => void onClosePosition()} disabled={submitting}>
            <Text style={styles.closeBtnText}>Fechar Posição</Text>
          </Pressable>
          <Pressable style={[styles.resetBtn, submitting && styles.actionBtnDisabled]} onPress={() => void onResetWallet()} disabled={submitting}>
            <Text style={styles.resetBtnText}>Resetar Carteira</Text>
          </Pressable>
        </View>
      ) : null}
    </ScrollView>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors'], darkMode: boolean) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 16 },
    content: { paddingBottom: 32 },
    badge: {
      alignSelf: 'center',
      backgroundColor: colors.warning,
      color: '#111827',
      fontWeight: '800',
      paddingVertical: 6,
      paddingHorizontal: 12,
      borderRadius: 6,
      marginBottom: 12,
    },
    ledgerHeader: {
      backgroundColor: colors.card,
      borderRadius: 12,
      padding: 14,
      borderWidth: 1,
      borderColor: colors.border,
    },
    ledgerLine: { color: colors.text, marginBottom: 6 },
    ledgerPnl: { fontSize: 22, fontWeight: '800', marginTop: 4 },
    quoteStatus: { color: colors.muted, fontSize: 12, marginTop: 6 },
    asset: { color: colors.muted, marginTop: 14 },
    assetHint: { color: colors.muted, fontSize: 12, marginTop: -8, marginBottom: 10 },
    pickerWrap: {
      backgroundColor: colors.card,
      borderRadius: 10,
      borderWidth: 1,
      borderColor: colors.border,
      marginTop: 8,
      marginBottom: 14,
    },
    picker: { color: colors.text },
    subtitle: { color: colors.text, marginTop: 8, marginBottom: 8, fontWeight: '700' },
    emptyText: { color: colors.muted, marginBottom: 6 },
    orderRow: {
      backgroundColor: darkMode ? '#0f172a' : '#ffffff',
      borderRadius: 10,
      borderColor: colors.border,
      borderWidth: 1,
      padding: 10,
      marginBottom: 8,
    },
    orderMain: { color: colors.text, fontSize: 13 },
    manualToggle: {
      marginTop: 16,
      backgroundColor: colors.cardSoft,
      borderColor: colors.border,
      borderWidth: 1,
      borderRadius: 10,
      padding: 12,
      alignItems: 'center',
    },
    manualToggleText: { color: colors.text, fontWeight: '700' },
    manualBox: { marginTop: 10 },
    qtyLabel: { color: colors.muted, marginBottom: 6 },
    qtyInput: {
      backgroundColor: colors.card,
      borderColor: colors.border,
      borderWidth: 1,
      borderRadius: 10,
      color: colors.text,
      paddingHorizontal: 10,
      paddingVertical: 8,
      marginBottom: 12,
    },
    actions: { flexDirection: 'row', gap: 10, marginBottom: 10 },
    actionBtn: { flex: 1, alignItems: 'center', padding: 12, borderRadius: 10 },
    actionBtnDisabled: { opacity: 0.65 },
    actionTxt: { color: '#fff', fontWeight: '800', fontSize: 18 },
    closeBtn: {
      backgroundColor: colors.cardSoft,
      borderWidth: 1,
      borderColor: colors.border,
      padding: 12,
      borderRadius: 10,
      alignItems: 'center',
      marginTop: 8,
    },
    closeBtnText: { color: colors.text, fontWeight: '700' },
    resetBtn: {
      backgroundColor: colors.danger,
      padding: 12,
      borderRadius: 10,
      alignItems: 'center',
      marginTop: 8,
    },
    resetBtnText: { color: '#fff', fontWeight: '700' },
    warnBanner: {
      backgroundColor: darkMode ? '#3a1111' : '#ffe8e8',
      borderColor: colors.danger,
      borderWidth: 1,
      borderRadius: 10,
      padding: 10,
      marginBottom: 10,
    },
    loadingInline: { marginBottom: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
    loadingText: { marginLeft: 8, color: colors.muted, fontSize: 12 },
    warnBannerText: { color: colors.danger, fontWeight: '600' },
    profit: { color: colors.success },
    loss: { color: colors.danger },
  });
