import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { useAppTheme } from '../theme';
import { BacktestScreen } from '../screens/BacktestScreen';
import { DashboardScreen } from '../screens/DashboardScreen';
import { LogsScreen } from '../screens/LogsScreen';
import { PaperTradingScreen } from '../screens/PaperTradingScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { StrategyScreen } from '../screens/StrategyScreen';

export type RootTabParamList = {
  Dashboard: undefined;
  Strategy: undefined;
  Backtest: undefined;
  Logs: undefined;
  Settings: undefined;
  Paper: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();

const iconByRoute: Record<keyof RootTabParamList, string> = {
  Dashboard: 'grid-outline',
  Strategy: 'options-outline',
  Backtest: 'stats-chart-outline',
  Logs: 'list-outline',
  Settings: 'settings-outline',
  Paper: 'cash-outline',
};

export function AppNavigator() {
  const { colors } = useAppTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: true,
        headerStyle: { backgroundColor: colors.card },
        headerTintColor: colors.text,
        tabBarStyle: { backgroundColor: colors.card, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.muted,
        tabBarIcon: ({ color, size }) => (
          <Ionicons name={iconByRoute[route.name as keyof RootTabParamList]} size={size} color={color} />
        ),
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Strategy" component={StrategyScreen} options={{ title: 'Strategy Config' }} />
      <Tab.Screen name="Backtest" component={BacktestScreen} options={{ title: 'Backtest Results' }} />
      <Tab.Screen name="Logs" component={LogsScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
      <Tab.Screen name="Paper" component={PaperTradingScreen} options={{ title: 'Paper Trading' }} />
    </Tab.Navigator>
  );
}
