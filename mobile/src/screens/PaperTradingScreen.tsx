import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Picker } from '@react-native-picker/picker';
import {
  fetchAssetUniverse,
  fetchPaperState,
  fetchStrategy,
  paperBuy,
  paperClosePosition,
  paperResetWallet,
  paperSell,
  PaperState,
} from '../services/api';
import { onConfigChanged } from '../services/events';
import { useAppTheme } from '../theme';

const ASSET_OPTIONS = ['PETR4', 'VALE3', 'ITUB4', 'BTC', 'ETH'];

export function PaperTradingScreen() {
  const { colors, darkMode } = useAppTheme();
  const [state, setState] = useState<PaperState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [asset, setAsset] = useState('PETR4');
  const [assetOptions, setAssetOptions] = useState<string[]>(ASSET_OPTIONS);
  const [orderQty, setOrderQty] = useState('1');
  const styles = useMemo(() => createStyles(colors, darkMode), [colors, darkMode]);
  const upperAsset = asset.toUpperCase();
  const isCrypto = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'AVAX', 'DOT'].includes(upperAsset);
  const currency = isCrypto ? 'USD' : 'BRL';
  const moneyFmt = useMemo(
    () => new Intl.NumberFormat('pt-BR', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    [currency]
  );

  const load = async (nextAsset = asset) => {
    const data = await fetchPaperState(nextAsset);
    setState(data);
  };

  useEffect(() => {
    (async () => {
      try {
        const [strategy, universe] = await Promise.all([fetchStrategy(), fetchAssetUniverse()]);
        if (universe.all?.length) setAssetOptions(universe.all);
        const nextAsset = strategy.asset?.toUpperCase?.() || 'PETR4';
        setAsset(nextAsset);
        await load(nextAsset);
      } catch {
        await load('PETR4');
      }
    })();
  }, []);

  useEffect(() => {
    const off = onConfigChanged(() => {
      void load(asset);
    });
    return off;
  }, [asset]);

  useFocusEffect(
    React.useCallback(() => {
      let active = true;
      const run = async () => {
        if (!active) return;
        await load(asset);
      };
      void run();
      const timer = setInterval(() => {
        void run();
      }, 5000);

      return () => {
        active = false;
        clearInterval(timer);
      };
    }, [asset])
  );

  useEffect(() => {
    void load(asset);
  }, [asset]);

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
      await load(asset);
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
      await load(asset);
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
      await load(asset);
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
      Alert.alert(
        'Carteira resetada',
        `Saldo voltou para ${moneyFmt.format(Number(next.balance ?? 0))} e posições foram zeradas.`
      );
    } catch (e: any) {
      Alert.alert('Falha ao resetar', e?.response?.data?.detail ?? 'Não foi possível resetar a carteira.');
    } finally {
      setSubmitting(false);
    }
  };

  const formatSignedMoney = (value: number) => `${value > 0 ? '+' : ''}${moneyFmt.format(value)}`;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.badge}>PAPER TRADING MODE</Text>
      <Text style={styles.asset}>Ativo em foco</Text>
      <View style={styles.pickerWrap}>
        <Picker selectedValue={asset} onValueChange={setAsset} dropdownIconColor={colors.text} style={styles.picker}>
          {assetOptions.map((a) => (
            <Picker.Item key={a} label={a} value={a} />
          ))}
        </Picker>
      </View>
      <Text style={styles.price}>{moneyFmt.format(Number(state?.current_price ?? 0))}</Text>
      <Text style={styles.quoteStatus}>{state?.price_status ?? 'Preço em Cache'}</Text>

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
          <Text style={styles.actionTxt}>{submitting ? '...' : 'BUY'}</Text>
        </Pressable>
        <Pressable
          style={[styles.actionBtn, { backgroundColor: colors.danger }, submitting && styles.actionBtnDisabled]}
          onPress={() => void onSell()}
          disabled={submitting}
        >
          <Text style={styles.actionTxt}>{submitting ? '...' : 'SELL'}</Text>
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text style={styles.line}>Saldo Simulado: {moneyFmt.format(Number(state?.balance ?? 0))}</Text>
        <Text style={styles.line}>
          P/L Flutuante:{' '}
          <Text
            style={
              (state?.floating_pnl ?? 0) > 0
                ? styles.profit
                : (state?.floating_pnl ?? 0) < 0
                ? styles.loss
                : styles.line
            }
          >
            {formatSignedMoney(Number(state?.floating_pnl ?? 0))}
          </Text>
        </Text>
        <Text style={styles.line}>
          Unidades na Carteira: {(state?.open_position_qty ?? 0).toFixed(2)} {state?.open_position_asset ?? '-'}
        </Text>
        <Text style={styles.line}>Preço Médio: {moneyFmt.format(Number(state?.avg_entry_price ?? 0))}</Text>
      </View>

      <Pressable
        style={[styles.closeBtn, submitting && styles.actionBtnDisabled]}
        onPress={() => void onClosePosition()}
        disabled={submitting}
      >
        <Text style={styles.closeBtnText}>Fechar Posição</Text>
      </Pressable>
      <Text style={styles.helpText}>Vende todas as unidades deste ativo a preço de mercado</Text>

      <Pressable
        style={[styles.resetBtn, submitting && styles.actionBtnDisabled]}
        onPress={() => void onResetWallet()}
        disabled={submitting}
      >
        <Text style={styles.resetBtnText}>Resetar Carteira</Text>
      </Pressable>
      <Text style={styles.helpText}>
        O modo Paper permite testar compras manuais usando saldo fictício, independente da ação do Bot.
      </Text>

      <Text style={styles.subtitle}>Ordens Simuladas Recentes</Text>
      {(state?.recent_orders ?? []).map((item) => (
        <View key={String(item.id)} style={styles.orderRow}>
          <Text style={styles.orderMain}>
            {item.side.toUpperCase()} {item.asset} @ {moneyFmt.format(Number(item.price ?? 0))}
          </Text>
          <Text style={styles.orderSub}>{new Date(item.created_at).toLocaleString()}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors'], darkMode: boolean) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 16 },
    content: { paddingBottom: 28 },
    badge: {
      alignSelf: 'center',
      backgroundColor: colors.warning,
      color: '#111827',
      fontWeight: '800',
      paddingVertical: 6,
      paddingHorizontal: 12,
      borderRadius: 6,
    },
    asset: { color: colors.muted, textAlign: 'center', marginTop: 14 },
    pickerWrap: {
      backgroundColor: colors.card,
      borderRadius: 10,
      borderWidth: 1,
      borderColor: colors.border,
      marginTop: 8,
    },
    picker: { color: colors.text },
    price: { color: colors.text, fontSize: 42, textAlign: 'center', marginBottom: 8 },
    quoteStatus: { color: colors.muted, textAlign: 'center', marginBottom: 8 },
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
    actions: { flexDirection: 'row', gap: 10, marginBottom: 14 },
    actionBtn: { flex: 1, alignItems: 'center', padding: 12, borderRadius: 10 },
    actionBtnDisabled: { opacity: 0.65 },
    actionTxt: { color: '#fff', fontWeight: '800', fontSize: 20 },
    card: { backgroundColor: colors.card, padding: 12, borderRadius: 10 },
    line: { color: colors.text, marginBottom: 6 },
    profit: { color: colors.success, fontWeight: '700' },
    loss: { color: colors.danger, fontWeight: '700' },
    closeBtn: {
      backgroundColor: colors.cardSoft,
      borderWidth: 1,
      borderColor: colors.border,
      padding: 12,
      borderRadius: 10,
      alignItems: 'center',
      marginTop: 10,
    },
    closeBtnText: { color: colors.text, fontWeight: '700' },
    helpText: { color: colors.muted, fontSize: 12, marginTop: 6, marginBottom: 6 },
    resetBtn: {
      backgroundColor: colors.danger,
      padding: 12,
      borderRadius: 10,
      alignItems: 'center',
      marginTop: 10,
    },
    resetBtnText: { color: '#fff', fontWeight: '700' },
    subtitle: { color: colors.text, marginTop: 16, marginBottom: 8, fontWeight: '700' },
    orderRow: {
      backgroundColor: darkMode ? '#0f172a' : '#ffffff',
      borderRadius: 10,
      borderColor: colors.border,
      borderWidth: 1,
      padding: 10,
      marginBottom: 8,
    },
    orderMain: { color: colors.text },
    orderSub: { color: colors.muted, fontSize: 12, marginTop: 3 },
  });
