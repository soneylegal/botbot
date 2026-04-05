import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { useStrategyContext } from '../context/StrategyContext';
import { useAppTheme } from '../theme';
import { emitConfigChanged } from '../services/events';
import { fetchAssetUniverse, saveStrategy } from '../services/api';

export function StrategyScreen() {
  const { colors } = useAppTheme();
  const [asset, setAsset] = useState('PETR4');
  const [timeframe, setTimeframe] = useState('5M');
  const [maShort, setMaShort] = useState(9);
  const [maLong, setMaLong] = useState(21);
  const [saving, setSaving] = useState(false);
  const [assets, setAssets] = useState<string[]>(['PETR4', 'VALE3', 'ITUB4']);
  const { strategy, loading: strategyLoading, setStrategyLocal } = useStrategyContext();

  useEffect(() => {
    (async () => {
      try {
        const universe = await fetchAssetUniverse();
        if (Array.isArray(universe?.all) && universe.all.length > 0) {
          setAssets(universe.all);
        }
      } catch {
        // preserve current local state on bootstrap failure
      }
    })();
  }, []);

  useEffect(() => {
    if (!strategy) return;
    if (typeof strategy.asset === 'string' && strategy.asset.length > 0) setAsset(strategy.asset);
    if (typeof strategy.timeframe === 'string' && strategy.timeframe.length > 0) setTimeframe(strategy.timeframe);
    if (typeof strategy.ma_short_period === 'number' && Number.isFinite(strategy.ma_short_period)) setMaShort(strategy.ma_short_period);
    if (typeof strategy.ma_long_period === 'number' && Number.isFinite(strategy.ma_long_period)) setMaLong(strategy.ma_long_period);
  }, [strategy]);

  const onSave = async () => {
    if (maLong <= maShort) {
      Alert.alert('Validação', 'A média longa deve ser maior que a curta.');
      return;
    }

    setSaving(true);
    try {
      const next = { asset, timeframe, ma_short_period: maShort, ma_long_period: maLong };
      await saveStrategy(next);
      setStrategyLocal(next);
      emitConfigChanged();
      Alert.alert('Sucesso', 'Estratégia salva.');
    } catch {
      Alert.alert('Falha', 'Não foi possível salvar a estratégia.');
    } finally {
      setSaving(false);
    }
  };

  const styles = useMemo(() => createStyles(colors), [colors]);

  if (strategyLoading) {
    return (
      <View style={styles.loaderWrap}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.helpText}>
        Defina a moeda e a janela de tempo que o Bot usará para operar e exibir no Dashboard.
      </Text>

      <Text style={styles.label}>Ativo</Text>
      <View style={styles.inputWrap}>
        <Picker selectedValue={asset} onValueChange={setAsset} dropdownIconColor={colors.text} style={styles.input}>
          {assets.map((symbol) => (
            <Picker.Item key={symbol} label={symbol} value={symbol} />
          ))}
        </Picker>
      </View>

      <Text style={styles.label}>Timeframe</Text>
      <View style={styles.inputWrap}>
        <Picker selectedValue={timeframe} onValueChange={setTimeframe} dropdownIconColor={colors.text} style={styles.input}>
          <Picker.Item label="1M" value="1M" />
          <Picker.Item label="5M" value="5M" />
          <Picker.Item label="1H" value="1H" />
          <Picker.Item label="1D" value="1D" />
        </Picker>
      </View>

      <Text style={styles.label}>MA Curta</Text>
      <TextInput
        value={String(maShort)}
        onChangeText={(v) => setMaShort(Number.parseInt(v.replace(/\D/g, ''), 10) || 0)}
        keyboardType="numeric"
        style={styles.numberInput}
      />

      <Text style={styles.label}>MA Longa</Text>
      <TextInput
        value={String(maLong)}
        onChangeText={(v) => setMaLong(Number.parseInt(v.replace(/\D/g, ''), 10) || 0)}
        keyboardType="numeric"
        style={styles.numberInput}
      />

      <Pressable style={[styles.button, saving && styles.buttonDisabled]} onPress={() => void onSave()} disabled={saving}>
        {saving ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.buttonText}>Salvar Estratégia</Text>}
      </Pressable>
    </ScrollView>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 16 },
    loaderWrap: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
    content: { paddingBottom: 28 },
    helpText: { color: colors.muted, marginBottom: 12, lineHeight: 20 },
    label: { color: colors.text, marginBottom: 8, marginTop: 10, fontSize: 15 },
    inputWrap: { borderRadius: 10, backgroundColor: colors.card, marginBottom: 8 },
    input: { color: colors.text },
    numberInput: {
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 10,
      color: colors.text,
      paddingHorizontal: 12,
      paddingVertical: 10,
    },
    button: { marginTop: 20, backgroundColor: colors.primary, borderRadius: 10, alignItems: 'center', padding: 14 },
    buttonDisabled: { opacity: 0.6 },
    buttonText: { color: '#fff', fontWeight: '700' },
  });
