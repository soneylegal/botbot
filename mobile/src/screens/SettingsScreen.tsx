import React, { useEffect, useState } from 'react';
import { Alert, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { fetchSettings, saveSettings, testConnection } from '../services/api';
import { colors } from '../theme';

export function SettingsScreen() {
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [exchangeName, setExchangeName] = useState('binance');
  const [tradeMode, setTradeMode] = useState<'paper' | 'live'>('paper');
  const [paperTrading, setPaperTrading] = useState(true);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    (async () => {
      const data = await fetchSettings();
      setApiKey(data.api_key_masked ?? '');
      setApiSecret(data.api_secret_masked ?? '');
      setExchangeName(data.exchange_name ?? 'binance');
      setTradeMode(data.trade_mode ?? 'paper');
      setPaperTrading(data.paper_trading);
      setDarkMode(data.dark_mode);
    })();
  }, []);

  const onSaveAndTest = async () => {
    await saveSettings({
      api_key: apiKey.includes('*') ? undefined : apiKey,
      api_secret: apiSecret.includes('*') ? undefined : apiSecret,
      exchange_name: exchangeName,
      trade_mode: tradeMode,
      paper_trading: paperTrading,
      dark_mode: darkMode,
    });
    const res = await testConnection();
    Alert.alert(res.ok ? 'Conexão OK' : 'Falha', res.message);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>API Key</Text>
      <TextInput
        value={apiKey}
        onChangeText={setApiKey}
        secureTextEntry
        placeholder="**************"
        placeholderTextColor={colors.muted}
        style={styles.input}
      />

      <Text style={styles.label}>API Secret</Text>
      <TextInput
        value={apiSecret}
        onChangeText={setApiSecret}
        secureTextEntry
        placeholder="**************"
        placeholderTextColor={colors.muted}
        style={styles.input}
      />

      <Text style={styles.label}>Exchange</Text>
      <TextInput
        value={exchangeName}
        onChangeText={setExchangeName}
        placeholder="binance"
        placeholderTextColor={colors.muted}
        style={styles.input}
        autoCapitalize="none"
      />

      <Text style={styles.label}>Modo de Execução</Text>
      <View style={styles.pickerWrap}>
        <Picker selectedValue={tradeMode} onValueChange={(v) => setTradeMode(v)} dropdownIconColor={colors.text} style={styles.input}>
          <Picker.Item label="Paper" value="paper" />
          <Picker.Item label="Live" value="live" />
        </Picker>
      </View>

      <TouchableOpacity style={styles.button} onPress={onSaveAndTest}>
        <Text style={styles.buttonText}>Salvar e Testar Conexão</Text>
      </TouchableOpacity>

      <View style={styles.toggleRow}>
        <Text style={styles.toggleLabel}>Paper Trading</Text>
        <Switch value={paperTrading} onValueChange={setPaperTrading} />
      </View>

      <View style={styles.toggleRow}>
        <Text style={styles.toggleLabel}>Dark Mode</Text>
        <Switch value={darkMode} onValueChange={setDarkMode} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: 16 },
  label: { color: colors.text, marginBottom: 8, marginTop: 10 },
  input: {
    backgroundColor: colors.card,
    borderColor: '#374151',
    borderWidth: 1,
    borderRadius: 10,
    color: colors.text,
    padding: 12,
  },
  pickerWrap: {
    backgroundColor: colors.card,
    borderColor: '#374151',
    borderWidth: 1,
    borderRadius: 10,
  },
  button: {
    backgroundColor: colors.primary,
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 12,
  },
  buttonText: { color: '#fff', fontWeight: '700' },
  toggleRow: {
    marginTop: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.card,
    padding: 12,
    borderRadius: 10,
  },
  toggleLabel: { color: colors.text, fontSize: 16 },
});
