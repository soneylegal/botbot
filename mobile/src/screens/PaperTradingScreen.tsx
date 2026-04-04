import React, { useEffect, useMemo, useState } from 'react';
import { Alert, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
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
import { emitConfigChanged, onConfigChanged } from '../services/events';
import { useAppTheme } from '../theme';

const QTY = 10;
const ASSET_OPTIONS = ['PETR4', 'VALE3', 'ITUB4', 'BTC', 'ETH'];

export function PaperTradingScreen() {
  const { colors, darkMode } = useAppTheme();
  const [state, setState] = useState<PaperState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [asset, setAsset] = useState('PETR4');
  const [assetOptions, setAssetOptions] = useState<string[]>(ASSET_OPTIONS);
  const styles = useMemo(() => createStyles(colors, darkMode), [colors, darkMode]);

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

  useEffect(() => {
    void load(asset);
    emitConfigChanged();
  }, [asset]);

  const onBuy = async () => {
    if (submitting) return;
    if (!state?.current_price || state.current_price <= 0) {
      Alert.alert('Preço indisponível', 'Não foi possível obter preço atual do ativo.');
      return;
    }
    setSubmitting(true);
    try {
      await paperBuy({ asset, price: state.current_price, quantity: QTY });
      await load(asset);
      Alert.alert('Ordem executada', `BUY ${asset} @ ${state.current_price.toFixed(2)}`);
    } catch (e: any) {
      Alert.alert('Falha na compra', e?.response?.data?.detail ?? 'Não foi possível executar a compra.');
    } finally {
      setSubmitting(false);
    }
  };

  const onSell = async () => {
    if (submitting) return;
    if (!state?.current_price || state.current_price <= 0) {
      Alert.alert('Preço indisponível', 'Não foi possível obter preço atual do ativo.');
      return;
    }
    setSubmitting(true);
    try {
      await paperSell({ asset, price: state.current_price, quantity: QTY });
      await load(asset);
      Alert.alert('Ordem executada', `SELL ${asset} @ ${state.current_price.toFixed(2)}`);
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
      Alert.alert('Carteira resetada', 'Saldo voltou para R$ 10.000,00 e posições foram zeradas.');
    } catch (e: any) {
      Alert.alert('Falha ao resetar', e?.response?.data?.detail ?? 'Não foi possível resetar a carteira.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.badge}>PAPER TRADING MODE</Text>
      <Text style={styles.asset}>Ativo em foco</Text>
      <View style={styles.pickerWrap}>
        <Picker selectedValue={asset} onValueChange={setAsset} dropdownIconColor={colors.text} style={styles.picker}>
          {assetOptions.map((a) => (
            <Picker.Item key={a} label={a} value={a} />
          ))}
        </Picker>
      </View>
      <Text style={styles.price}>R$ {(state?.current_price ?? 0).toFixed(2)}</Text>
      <Text style={styles.quoteStatus}>{state?.price_status ?? 'Preço em Cache'}</Text>

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
        <Text style={styles.line}>Saldo Simulado: R$ {state?.balance?.toFixed(2) ?? '0.00'}</Text>
        <Text style={styles.line}>
          P/L Flutuante:{' '}
          <Text style={(state?.floating_pnl ?? 0) >= 0 ? styles.profit : styles.loss}>
            R$ {(state?.floating_pnl ?? 0).toFixed(2)}
          </Text>
        </Text>
        <Text style={styles.line}>
          Posição Aberta: {(state?.open_position_qty ?? 0).toFixed(2)} {state?.open_position_asset ?? '-'}
        </Text>
        <Text style={styles.line}>Preço Médio: R$ {(state?.avg_entry_price ?? 0).toFixed(2)}</Text>
      </View>

      <Pressable
        style={[styles.closeBtn, submitting && styles.actionBtnDisabled]}
        onPress={() => void onClosePosition()}
        disabled={submitting}
      >
        <Text style={styles.closeBtnText}>Fechar Posição</Text>
      </Pressable>

      <Pressable
        style={[styles.resetBtn, submitting && styles.actionBtnDisabled]}
        onPress={() => void onResetWallet()}
        disabled={submitting}
      >
        <Text style={styles.resetBtnText}>Resetar Carteira</Text>
      </Pressable>

      <Text style={styles.subtitle}>Ordens Simuladas Recentes</Text>
      <FlatList
        data={state?.recent_orders ?? []}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <View style={styles.orderRow}>
            <Text style={styles.orderMain}>
              {item.side.toUpperCase()} {item.asset} @ {item.price}
            </Text>
            <Text style={styles.orderSub}>{new Date(item.created_at).toLocaleString()}</Text>
          </View>
        )}
      />
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors'], darkMode: boolean) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 16 },
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
