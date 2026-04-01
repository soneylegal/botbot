import React, { useEffect, useState } from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { fetchLogs, LogRow } from '../services/api';
import { colors } from '../theme';

const levelConfig = {
  success: { icon: 'checkmark-circle', bg: '#14532d' },
  error: { icon: 'close-circle', bg: '#7f1d1d' },
  info: { icon: 'information-circle', bg: '#374151' },
  warning: { icon: 'alert-circle', bg: '#78350f' },
};

export function LogsScreen() {
  const [rows, setRows] = useState<LogRow[]>([]);

  useEffect(() => {
    (async () => {
      const data = await fetchLogs();
      setRows(data);
    })();
  }, []);

  return (
    <FlatList
      data={rows}
      keyExtractor={(item) => String(item.id)}
      style={styles.list}
      renderItem={({ item }) => {
        const cfg = levelConfig[item.level] ?? levelConfig.info;
        return (
          <View style={[styles.row, { backgroundColor: cfg.bg }]}>
            <Ionicons name={cfg.icon} size={20} color="#fff" style={{ marginRight: 10 }} />
            <View style={{ flex: 1 }}>
              <Text style={styles.message}>{item.message}</Text>
              <Text style={styles.time}>{new Date(item.created_at).toLocaleString()}</Text>
            </View>
          </View>
        );
      }}
      ListEmptyComponent={<Text style={styles.empty}>Sem logs ainda.</Text>}
    />
  );
}

const styles = StyleSheet.create({
  list: { flex: 1, backgroundColor: colors.bg, padding: 10 },
  row: {
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  message: { color: '#fff', fontSize: 15, fontWeight: '600' },
  time: { color: '#e5e7eb', fontSize: 12, marginTop: 4 },
  empty: { color: colors.muted, textAlign: 'center', marginTop: 30 },
});
