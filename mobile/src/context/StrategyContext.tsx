import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchStrategy, StrategyConfig } from '../services/api';
import { onConfigChanged } from '../services/events';

type StrategyContextValue = {
  strategy: StrategyConfig | null;
  loading: boolean;
  refreshStrategy: () => Promise<void>;
  setStrategyLocal: (next: StrategyConfig) => void;
};

const StrategyContext = createContext<StrategyContextValue | undefined>(undefined);

export function StrategyProvider({ children }: { children: React.ReactNode }) {
  const [strategy, setStrategy] = useState<StrategyConfig | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshStrategy = useCallback(async () => {
    try {
      setLoading(true);
      const next = await fetchStrategy();
      setStrategy(next);
    } catch {
      // Keep last known strategy if request fails.
    } finally {
      setLoading(false);
    }
  }, []);

  const setStrategyLocal = useCallback((next: StrategyConfig) => {
    setStrategy(next);
  }, []);

  useEffect(() => {
    void refreshStrategy();
  }, [refreshStrategy]);

  useEffect(() => {
    const off = onConfigChanged(() => {
      void refreshStrategy();
    });
    return off;
  }, [refreshStrategy]);

  const value = useMemo(
    () => ({ strategy, loading, refreshStrategy, setStrategyLocal }),
    [strategy, loading, refreshStrategy, setStrategyLocal]
  );

  return <StrategyContext.Provider value={value}>{children}</StrategyContext.Provider>;
}

export function useStrategyContext() {
  const ctx = useContext(StrategyContext);
  if (!ctx) {
    throw new Error('useStrategyContext must be used inside StrategyProvider');
  }
  return ctx;
}
