import React from 'react';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { AppNavigator } from './src/navigation/AppNavigator';
import { colors } from './src/theme';

const navTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.bg,
    card: colors.card,
    text: colors.text,
    primary: colors.primary,
    border: '#1f2937',
  },
};

export default function App() {
  return (
    <NavigationContainer theme={navTheme}>
      <StatusBar style="light" />
      <AppNavigator />
    </NavigationContainer>
  );
}
