import React, { useMemo, useState } from 'react';
import { ActivityIndicator, Alert, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { useAppTheme } from '../theme';
import { loginWithCredentials, registerUser } from '../services/api';

type Props = {
  onAuthenticated: () => void;
};

export function LoginScreen({ onAuthenticated }: Props) {
  const { colors } = useAppTheme();
  const [email, setEmail] = useState('admin@botbot.local');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const styles = useMemo(() => createStyles(colors), [colors]);

  const doLogin = async () => {
    setLoading(true);
    try {
      await loginWithCredentials(email.trim(), password);
      onAuthenticated();
    } catch {
      Alert.alert('Falha no login', 'Não foi possível autenticar. Verifique API/credenciais.');
    } finally {
      setLoading(false);
    }
  };

  const doRegisterAndLogin = async () => {
    setLoading(true);
    try {
      await registerUser(email.trim(), password);
      await loginWithCredentials(email.trim(), password);
      onAuthenticated();
    } catch {
      Alert.alert('Falha', 'Não foi possível registrar/autenticar.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Bot de Swing Trade</Text>
      <Text style={styles.subtitle}>Autenticação</Text>

      <TextInput
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="email"
        placeholderTextColor={colors.muted}
        style={styles.input}
      />

      <TextInput
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        placeholder="senha"
        placeholderTextColor={colors.muted}
        style={styles.input}
      />

      <TouchableOpacity style={styles.button} onPress={doLogin} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Entrar</Text>}
      </TouchableOpacity>

      <TouchableOpacity style={styles.buttonSecondary} onPress={doRegisterAndLogin} disabled={loading}>
        <Text style={styles.buttonSecondaryText}>Registrar + Entrar</Text>
      </TouchableOpacity>
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bg, padding: 20, justifyContent: 'center' },
    title: { color: colors.text, fontSize: 28, fontWeight: '700', textAlign: 'center' },
    subtitle: { color: colors.muted, fontSize: 16, textAlign: 'center', marginBottom: 20 },
    input: {
      backgroundColor: colors.card,
      borderColor: colors.border,
      borderWidth: 1,
      borderRadius: 10,
      color: colors.text,
      padding: 12,
      marginBottom: 12,
    },
    button: { backgroundColor: colors.primary, borderRadius: 10, alignItems: 'center', padding: 14, marginTop: 6 },
    buttonText: { color: '#fff', fontWeight: '700' },
    buttonSecondary: { alignItems: 'center', padding: 12, marginTop: 10 },
    buttonSecondaryText: { color: colors.muted },
  });
