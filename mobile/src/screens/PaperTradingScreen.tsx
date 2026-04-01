import React, { useEffect, useState } from 'react';
import { Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { fetchPaperState, paperBuy, paperSell, PaperState } from '../services/api';
import { colors } from '../theme';

const ASSET = 'PETR4';
const PRICE = 25.5;
const QTY = 10;

export function PaperTradingScreen() {
  const [state, setState] = useState<PaperState | null>(null);

  const load = async () => {
    const data = await fetchPaperState();
    setState(data);
  };

  useEffect(() => {
    load();
  }, []);

  const onBuy = async () => {
    await paperBuy({ asset: ASSET, price: PRICE, quantity: QTY });
    Alert.alert('Ordem executada', `BUY ${ASSET} @ ${PRICE}`);
    load();
  };

  const onSell = async () => {
    await paperSell({ asset: ASSET, price: PRICE, quantity: QTY });
    Alert.alert('Ordem executada', `SELL ${ASSET} @ ${PRICE}`);
    load();
  };

  return (
    <View style={styles.container}>
      <Text style={styles.badge}>PAPER TRADING MODE</Text>
      <Text style={styles.asset}>{ASSET}</Text>
      <Text style={styles.price}>R$ {PRICE.toFixed(2)}</Text>

      <View style={styles.actions}>
        <TouchableOpacity style={[styles.actionBtn, { backgroundColor: colors.success }]} onPress={onBuy}>
          <Text style={styles.actionTxt}>BUY</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.actionBtn, { backgroundColor: colors.danger }]} onPress={onSell}>
          <Text style={styles.actionTxt}>SELL</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.line}>Saldo Simulado: R$ {state?.balance?.toFixed(2) ?? '0.00'}</Text>
        <Text style={styles.line}>
          Posição Aberta: {(state?.open_position_qty ?? 0).toFixed(2)} {state?.open_position_asset ?? '-'}
        </Text>
      </View>

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

const styles = StyleSheet.create({
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
  price: { color: colors.text, fontSize: 42, textAlign: 'center', marginBottom: 12 },
  actions: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  actionBtn: { flex: 1, alignItems: 'center', padding: 12, borderRadius: 10 },
  actionTxt: { color: '#fff', fontWeight: '800', fontSize: 20 },
  card: { backgroundColor: colors.card, padding: 12, borderRadius: 10 },
  line: { color: colors.text, marginBottom: 6 },
  subtitle: { color: colors.text, marginTop: 16, marginBottom: 8, fontWeight: '700' },
  orderRow: {
    backgroundColor: '#0f172a',
    borderRadius: 10,
    borderColor: '#1f2937',
    borderWidth: 1,
    padding: 10,
    marginBottom: 8,
  },
  orderMain: { color: colors.text },
  orderSub: { color: colors.muted, fontSize: 12, marginTop: 3 },
});
