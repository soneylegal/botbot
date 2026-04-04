type ConfigListener = () => void;

const listeners = new Set<ConfigListener>();

export function emitConfigChanged() {
  listeners.forEach((listener) => {
    try {
      listener();
    } catch {
      // ignore listener errors
    }
  });
}

export function onConfigChanged(listener: ConfigListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
