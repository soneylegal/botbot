import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Pressable, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { fetchSettings, paperResetWallet, saveSettings, testConnection } from '../services/api';
import { emitConfigChanged } from '../services/events';
import { useAppTheme } from '../theme';

export function SettingsScreen() {
  const { colors, setDarkMode: setGlobalDarkMode } = useAppTheme();
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [exchangeName, setExchangeName] = useState('binance');
  const [tradeMode, setTradeMode] = useState<'paper' | 'live'>('paper');
  const [paperTrading, setPaperTrading] = useState(true);
  const [darkMode, setDarkModeLocal] = useState(true);
  const [testing, setTesting] = useState(false);
  const [initialSimBalance, setInitialSimBalance] = useState('10000');

  useEffect(() => {
    (async () => {
      const data = await fetchSettings();
      setApiKey(data.api_key_masked ?? '');
      setApiSecret(data.api_secret_masked ?? '');
      setExchangeName(data.exchange_name ?? 'binance');
      setTradeMode(data.trade_mode ?? 'paper');
      setPaperTrading(data.paper_trading);
      setDarkModeLocal(Boolean(data.dark_mode));
      setGlobalDarkMode(Boolean(data.dark_mode));
    })();
  }, [setGlobalDarkMode]);

  const onSaveAndTest = async () => {
    setTesting(true);
    try {
      await saveSettings({
        api_key: apiKey.includes('*') ? undefined : apiKey,
        api_secret: apiSecret.includes('*') ? undefined : apiSecret,
        exchange_name: exchangeName,
        trade_mode: tradeMode,
        paper_trading: paperTrading,
        dark_mode: darkMode,
      });
      emitConfigChanged();
      const res = await testConnection();
      setGlobalDarkMode(darkMode);
      if (res.ok) {
        Alert.alert('Conexão OK', `Conexão OK com ${exchangeName}. ${res.message}`);
      } else {
        Alert.alert('Falha na conexão', `${exchangeName}: ${res.message}`);
      }
    } catch (e: any) {
      const summary = e?.response?.data?.detail ?? e?.message ?? 'Erro inesperado';
      Alert.alert('Erro técnico', `Não foi possível salvar/testar. ${summary}`);
    } finally {
      setTesting(false);
    }
  };

  const onResetPaperWithBalance = async () => {
    const parsed = Number(initialSimBalance.replace(',', '.'));
    if (!Number.isFinite(parsed) || parsed <= 0) {
      Alert.alert('Valor inválido', 'Informe um saldo inicial maior que zero.');
      return;
    }
    setTesting(true);
    try {
      await paperResetWallet(parsed);
      Alert.alert('Carteira resetada', `Novo saldo inicial aplicado: R$ ${parsed.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
    } catch (e: any) {
      const summary = e?.response?.data?.detail ?? e?.message ?? 'Erro inesperado';
      Alert.alert('Erro técnico', `Não foi possível resetar a carteira. ${summary}`);
    } finally {
      setTesting(false);
    }
  };

  const styles = useMemo(() => createStyles(colors), [colors]);

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
      <Text style={styles.helpText}>Paper = simulado no banco local. Live = envia ordem para exchange com dinheiro real.</Text>
      <View style={styles.pickerWrap}>
        <Picker selectedValue={tradeMode} onValueChange={(v) => setTradeMode(v)} dropdownIconColor={colors.text} style={styles.input}>
          <Picker.Item label="Paper" value="paper" />
          <Picker.Item label="Live" value="live" />
        </Picker>
      </View>

      <Text style={styles.label}>Saldo Inicial Simulado</Text>
      <TextInput
        value={initialSimBalance}
        onChangeText={setInitialSimBalance}
        keyboardType="numeric"
        placeholder="10000"
        placeholderTextColor={colors.muted}
        style={styles.input}
      />

      <Pressable style={[styles.button, testing && styles.buttonDisabled]} onPress={() => void onSaveAndTest()} disabled={testing}>
        <Text style={styles.buttonText}>{testing ? 'Testando conexão...' : 'Salvar e Testar Conexão'}</Text>
      </Pressable>

      <Pressable style={[styles.secondaryButton, testing && styles.buttonDisabled]} onPress={() => void onResetPaperWithBalance()} disabled={testing}>
        <Text style={styles.secondaryButtonText}>Resetar Carteira com Saldo Inicial</Text>
      </Pressable>

      <View style={styles.toggleRow}>
        <View style={{ flex: 1, paddingRight: 8 }}>
          <Text style={styles.toggleLabel}>Paper Trading</Text>
          <Text style={styles.helpText}>Se desativado, o bot tenta operar em Live usando API Key e API Secret.</Text>
        </View>
        <Switch value={paperTrading} onValueChange={setPaperTrading} />
      </View>

      <View style={styles.toggleRow}>
        <Text style={styles.toggleLabel}>Dark Mode</Text>
        <Switch
          value={darkMode}
          onValueChange={(v) => {
            setDarkModeLocal(v);
            setGlobalDarkMode(v);
          }}
        />
      </View>
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 16 },
    label: { color: colors.text, marginBottom: 8, marginTop: 10 },
    input: {
      backgroundColor: colors.card,
      borderColor: colors.border,
      borderWidth: 1,
      borderRadius: 10,
      color: colors.text,
      padding: 12,
    },
    pickerWrap: {
      backgroundColor: colors.card,
      borderColor: colors.border,
      borderWidth: 1,
      borderRadius: 10,
    },
    button: {
      backgroundColor: colors.primary,
      padding: 14,
      borderRadius: 10,
      alignItems: 'center',
      marginTop: 20,
      marginBottom: 10,
    },
    secondaryButton: {
      backgroundColor: colors.cardSoft,
      borderWidth: 1,
      borderColor: colors.border,
      padding: 12,
      borderRadius: 10,
      alignItems: 'center',
      marginBottom: 12,
    },
    buttonDisabled: { opacity: 0.65 },
    buttonText: { color: '#fff', fontWeight: '700' },
    secondaryButtonText: { color: colors.text, fontWeight: '700' },
    helpText: { color: colors.muted, marginBottom: 6, fontSize: 12 },
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
