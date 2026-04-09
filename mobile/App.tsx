import 'react-native-gesture-handler';
import React, { useEffect, useState } from 'react';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { AppNavigator } from './src/navigation/AppNavigator';
import { StrategyProvider } from './src/context/StrategyContext';
import { LoginScreen } from './src/screens/LoginScreen';
import { emitConfigChanged } from './src/services/events';
import { clearVisualCacheOnColdStart, fetchSettings } from './src/services/api';
import { ThemeProvider, useAppTheme } from './src/theme';

function RootApp() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const { colors, darkMode, setDarkMode } = useAppTheme();

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.title = 'Swing Trade Bot';
    }
  }, []);

  useEffect(() => {
    void clearVisualCacheOnColdStart();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    emitConfigChanged();
    (async () => {
      try {
        const settings = await fetchSettings();
        setDarkMode(Boolean(settings.dark_mode));
      } catch {
        // keep current theme on startup failure
      }
    })();
  }, [isAuthenticated, setDarkMode]);

  const navTheme = {
    ...DefaultTheme,
    colors: {
      ...DefaultTheme.colors,
      background: colors.bg,
      card: colors.card,
      text: colors.text,
      primary: colors.primary,
      border: colors.border,
    },
  };

  return (
    <NavigationContainer theme={navTheme}>
      <StatusBar style={darkMode ? 'light' : 'dark'} />
      {isAuthenticated ? <AppNavigator /> : <LoginScreen onAuthenticated={() => setIsAuthenticated(true)} />}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ThemeProvider>
        <StrategyProvider>
          <RootApp />
        </StrategyProvider>
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}
