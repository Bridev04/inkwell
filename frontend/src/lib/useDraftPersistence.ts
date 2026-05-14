import { useState, useEffect, useRef } from 'react';

// [value, set, clear]
// set: debounced 500ms write to sessionStorage (not localStorage — avoids stale cross-session drafts)
// clear: synchronous wipe + state reset
export function useDraftPersistence(
  key: string,
  initial = ''
): [string, (value: string) => void, () => void] {
  const [value, setValue] = useState(initial);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Hydrate from sessionStorage on mount — SSR-safe (no window access during render).
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(key);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (stored !== null) setValue(stored);
    } catch {
      // sessionStorage may be unavailable (e.g., private browsing restrictions)
    }
  }, [key]);

  function set(newValue: string): void {
    setValue(newValue);
    if (debounceRef.current !== null) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      try {
        sessionStorage.setItem(key, newValue);
      } catch {}
    }, 500);
  }

  function clear(): void {
    if (debounceRef.current !== null) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setValue(initial);
    try {
      sessionStorage.removeItem(key);
    } catch {}
  }

  return [value, set, clear];
}
