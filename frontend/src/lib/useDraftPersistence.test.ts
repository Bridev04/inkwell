import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDraftPersistence } from './useDraftPersistence';

// Minimal sessionStorage stub for jsdom (jsdom supports it natively, but we
// reset between tests for isolation).
beforeEach(() => {
  sessionStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useDraftPersistence', () => {
  it('starts with the initial value and empty sessionStorage', () => {
    const { result } = renderHook(() =>
      useDraftPersistence('test-key', 'init')
    );
    expect(result.current[0]).toBe('init');
  });

  it('hydrates from sessionStorage on mount', () => {
    sessionStorage.setItem('test-key', 'stored value');
    const { result } = renderHook(() =>
      useDraftPersistence('test-key', '')
    );
    // Hydration happens in useEffect (after render)
    act(() => {});
    expect(result.current[0]).toBe('stored value');
  });

  it('writes to sessionStorage after debounce when setter is called', () => {
    const { result } = renderHook(() =>
      useDraftPersistence('test-key', '')
    );

    act(() => {
      result.current[1]('hello');
    });

    // Not yet written before debounce fires
    expect(sessionStorage.getItem('test-key')).toBeNull();

    // Advance past debounce
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(sessionStorage.getItem('test-key')).toBe('hello');
  });

  it('clears state and sessionStorage when clear() is called', () => {
    sessionStorage.setItem('test-key', 'persisted');
    const { result } = renderHook(() =>
      useDraftPersistence('test-key', 'initial')
    );

    act(() => {
      result.current[1]('modified');
    });
    act(() => {
      vi.advanceTimersByTime(500);
    });

    act(() => {
      result.current[2](); // clear
    });

    expect(result.current[0]).toBe('initial');
    expect(sessionStorage.getItem('test-key')).toBeNull();
  });
});
