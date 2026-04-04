import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import Slider from '@react-native-community/slider';
import { Picker } from '@react-native-picker/picker';
import { useAppTheme } from '../theme';
import { emitConfigChanged } from '../services/events';
import { fetchAssetUniverse, fetchStrategy, saveStrategy } from '../services/api';

export function StrategyScreen() {
  const { colors } = useAppTheme();
  const [asset, setAsset] = useState('PETR4');
  const [timeframe, setTimeframe] = useState('5M');
  const [maShort, setMaShort] = useState(9);
  const [maLong, setMaLong] = useState(21);
  const [saving, setSaving] = useState(false);
  const [assets, setAssets] = useState<string[]>(['PETR4', 'VALE3', 'ITUB4']);

  useEffect(() => {
    (async () => {
      try {
        const [data, universe] = await Promise.all([fetchStrategy(), fetchAssetUniverse()]);
        setAssets(universe.all);
        setAsset(data.asset);
        setTimeframe(data.timeframe);
        setMaShort(data.ma_short_period);
        setMaLong(data.ma_long_period);
      } catch {
        const data = await fetchStrategy();
        setAsset(data.asset);
        setTimeframe(data.timeframe);
        setMaShort(data.ma_short_period);
        setMaLong(data.ma_long_period);
      }
    })();
  }, []);

  const onSave = async () => {
    if (maLong <= maShort) {
      Alert.alert('Validação', 'A média longa deve ser maior que a curta.');
      return;
    }

    setSaving(true);
    try {
      await saveStrategy({ asset, timeframe, ma_short_period: maShort, ma_long_period: maLong });
      emitConfigChanged();
      Alert.alert('Sucesso', 'Estratégia salva.');
    } catch {
      Alert.alert('Falha', 'Não foi possível salvar a estratégia.');
    } finally {
      setSaving(false);
    }
  };

  const styles = useMemo(() => createStyles(colors), [colors]);

  return (
    <View style={styles.container}>
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
        <Picker
          selectedValue={timeframe}
          onValueChange={setTimeframe}
          dropdownIconColor={colors.text}
          style={styles.input}
        >
          <Picker.Item label="1M" value="1M" />
          <Picker.Item label="5M" value="5M" />
          <Picker.Item label="1H" value="1H" />
          <Picker.Item label="1D" value="1D" />
        </Picker>
      </View>

      <Text style={styles.label}>MA Curta: {maShort}</Text>
      <Slider minimumValue={3} maximumValue={50} step={1} value={maShort} onValueChange={setMaShort} minimumTrackTintColor={colors.primary} />

      <Text style={styles.label}>MA Longa: {maLong}</Text>
      <Slider minimumValue={5} maximumValue={200} step={1} value={maLong} onValueChange={setMaLong} minimumTrackTintColor={colors.primary} />

      <Pressable style={[styles.button, saving && styles.buttonDisabled]} onPress={() => void onSave()} disabled={saving}>
        <Text style={styles.buttonText}>{saving ? 'Salvando...' : 'Salvar Estratégia'}</Text>
      </Pressable>
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 16 },
    label: { color: colors.text, marginBottom: 8, marginTop: 10, fontSize: 15 },
    inputWrap: { borderRadius: 10, backgroundColor: colors.card, marginBottom: 8 },
    input: { color: colors.text },
    button: { marginTop: 20, backgroundColor: colors.primary, borderRadius: 10, alignItems: 'center', padding: 14 },
    buttonDisabled: { opacity: 0.6 },
    buttonText: { color: '#fff', fontWeight: '700' },
  });
