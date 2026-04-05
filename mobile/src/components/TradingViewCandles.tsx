import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';

type CandlePoint = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

type IndicatorPoint = {
  time: string;
  value: number;
};

type Props = {
  candles: CandlePoint[];
  maShort?: IndicatorPoint[];
  maLong?: IndicatorPoint[];
  height?: number;
  darkMode?: boolean;
};

function toUnixSeconds(value: string) {
  const t = Date.parse(value);
  if (Number.isNaN(t)) return 0;
  return Math.floor(t / 1000);
}

function sanitizeCandles(input: CandlePoint[]) {
  const map = new Map<number, { time: number; open: number; high: number; low: number; close: number }>();
  for (const c of input) {
    const t = toUnixSeconds(c.time);
    const open = Number(c.open);
    const high = Number(c.high);
    const low = Number(c.low);
    const close = Number(c.close);
    if (!Number.isFinite(t) || t <= 0) continue;
    if (![open, high, low, close].every((v) => Number.isFinite(v) && v > 0)) continue;
    map.set(t, {
      time: t,
      open,
      high: Math.max(high, open, close),
      low: Math.min(low, open, close),
      close,
    });
  }
  return Array.from(map.values()).sort((a, b) => a.time - b.time);
}

function sanitizeLine(input: IndicatorPoint[] = []) {
  const map = new Map<number, { time: number; value: number }>();
  for (const p of input) {
    const t = toUnixSeconds(p.time);
    const value = Number(p.value);
    if (!Number.isFinite(t) || t <= 0) continue;
    if (!Number.isFinite(value) || value <= 0) continue;
    map.set(t, { time: t, value });
  }
  return Array.from(map.values()).sort((a, b) => a.time - b.time);
}

export function TradingViewCandles({
  candles,
  maShort = [],
  maLong = [],
  height = 280,
  darkMode = false,
}: Props) {
  const html = useMemo(() => {
    const candleData = sanitizeCandles(candles);
    const shortData = sanitizeLine(maShort);
    const longData = sanitizeLine(maLong);

    const bg = darkMode ? '#0b0f1a' : '#ffffff';
    const text = darkMode ? '#94a3b8' : '#334155';
    const grid = darkMode ? '#1f2937' : '#e2e8f0';

    return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <style>
      html, body {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        background: ${bg};
        overflow: hidden;
        overscroll-behavior: none;
        touch-action: none;
      }
      #chart { width: 100%; height: 100%; }
      #legend {
        position: absolute;
        top: 10px;
        left: 10px;
        z-index: 10;
        color: #fff;
        font-family: sans-serif;
        font-size: 12px;
        background: rgba(0,0,0,0.5);
        padding: 5px;
        border-radius: 4px;
      }
      #error {
        position: absolute;
        bottom: 10px;
        left: 10px;
        right: 10px;
        color: #fecaca;
        font-family: sans-serif;
        font-size: 12px;
        display: none;
      }
    </style>
    <script src="https://unpkg.com/lightweight-charts@4.2.2/dist/lightweight-charts.standalone.production.js"></script>
  </head>
  <body>
    <div id="legend">Velas | MA Curta (azul) | MA Longa (laranja)</div>
    <div id="chart"></div>
    <div id="error"></div>
    <script>
      const errorEl = document.getElementById('error');
      const chartEl = document.getElementById('chart');
      const candles = ${JSON.stringify(candleData)};
      const maShort = ${JSON.stringify(shortData)};
      const maLong = ${JSON.stringify(longData)};

      function fail(msg) {
        if (!errorEl) return;
        errorEl.style.display = 'block';
        errorEl.innerText = msg;
      }

      try {
        if (!window.LightweightCharts || !candles.length) {
          fail(candles.length ? 'Falha ao carregar motor gráfico.' : 'Sem candles para renderizar.');
        } else {
          const chart = window.LightweightCharts.createChart(chartEl, {
            autoSize: true,
            layout: { background: { color: '${bg}' }, textColor: '${text}' },
            grid: { vertLines: { color: '${grid}' }, horzLines: { color: '${grid}' } },
            rightPriceScale: { borderColor: '${grid}', autoScale: true },
            timeScale: { borderColor: '${grid}', timeVisible: true, secondsVisible: false, rightOffset: 2 },
            handleScroll: { vertTouchDrag: false },
            handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
            localization: { locale: 'pt-BR' },
          });

          const candleSeries = chart.addCandlestickSeries({
            upColor: '#16a34a',
            downColor: '#dc2626',
            borderVisible: false,
            wickUpColor: '#16a34a',
            wickDownColor: '#dc2626',
            priceLineVisible: true,
          });
          candleSeries.setData(candles);

          const shortSeries = chart.addLineSeries({ color: '#2563eb', lineWidth: 2, priceLineVisible: false });
          const longSeries = chart.addLineSeries({ color: '#f59e0b', lineWidth: 2, priceLineVisible: false });
          shortSeries.setData(maShort);
          longSeries.setData(maLong);

          chart.timeScale().fitContent();
          window.addEventListener('resize', () => chart.timeScale().fitContent());
        }
      } catch (e) {
        fail('Erro ao renderizar gráfico: ' + (e && e.message ? e.message : 'desconhecido'));
      }
    </script>
  </body>
</html>`;
  }, [candles, darkMode, maLong, maShort]);

  return (
    <View style={[styles.wrap, { height }]}> 
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        javaScriptEnabled
        domStorageEnabled
        style={styles.webview}
        scrollEnabled={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
    overflow: 'hidden',
    borderRadius: 12,
  },
  webview: {
    flex: 1,
    backgroundColor: 'transparent',
  },
});
