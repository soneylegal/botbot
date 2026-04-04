import React, { createContext, useContext, useMemo, useState } from 'react';

export type AppColors = {
  bg: string;
  card: string;
  cardSoft: string;
  text: string;
  muted: string;
  primary: string;
  success: string;
  danger: string;
  warning: string;
  border: string;
};

const darkColors: AppColors = {
  bg: '#0b0f1a',
  card: '#111827',
  cardSoft: '#1f2937',
  text: '#f3f4f6',
  muted: '#9ca3af',
  primary: '#3b82f6',
  success: '#22c55e',
  danger: '#ef4444',
  warning: '#f59e0b',
  border: '#1f2937',
};

const lightColors: AppColors = {
  bg: '#f8fafc',
  card: '#ffffff',
  cardSoft: '#eef2ff',
  text: '#0f172a',
  muted: '#64748b',
  primary: '#2563eb',
  success: '#16a34a',
  danger: '#dc2626',
  warning: '#d97706',
  border: '#e2e8f0',
};

type ThemeContextValue = {
  darkMode: boolean;
  setDarkMode: (v: boolean) => void;
  colors: AppColors;
};

const ThemeContext = createContext<ThemeContextValue>({
  darkMode: true,
  setDarkMode: () => undefined,
  colors: darkColors,
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [darkMode, setDarkMode] = useState(true);
  const value = useMemo(
    () => ({ darkMode, setDarkMode, colors: darkMode ? darkColors : lightColors }),
    [darkMode]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useAppTheme() {
  return useContext(ThemeContext);
}

export const colors = darkColors;
