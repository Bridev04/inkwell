import { useSyncExternalStore } from 'react';

const STORAGE_KEY = 'draftwell:saved-docs';

export interface SavedDocRef {
  id: string;
  createdAt: string;
  snippet: string;
}

// Stable empty-array reference for server snapshot and initial empty state.
const EMPTY: SavedDocRef[] = [];

// ---------------------------------------------------------------------------
// Internal pub/sub — notifies same-tab subscribers after writes.
// Cross-tab changes come via the `storage` window event in `subscribe()`.
// ---------------------------------------------------------------------------

const internalSubscribers = new Set<() => void>();

function notifySubscribers(): void {
  internalSubscribers.forEach((cb) => cb());
}

// ---------------------------------------------------------------------------
// Low-level read/write helpers
// ---------------------------------------------------------------------------

function read(): SavedDocRef[] {
  if (typeof window === 'undefined') return EMPTY;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedDocRef[]) : EMPTY;
  } catch {
    return EMPTY;
  }
}

function write(docs: SavedDocRef[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(docs));
  notifySubscribers();
}

// ---------------------------------------------------------------------------
// useSyncExternalStore plumbing
// ---------------------------------------------------------------------------

// Stable snapshot cache: avoids returning a new array reference on every call
// (React tears if getSnapshot is not referentially stable when data is unchanged).
let cachedRaw = '';
let cachedDocs: SavedDocRef[] = EMPTY;

function getSnapshot(): SavedDocRef[] {
  const raw = typeof window !== 'undefined' ? (localStorage.getItem(STORAGE_KEY) ?? '') : '';
  if (raw === cachedRaw) return cachedDocs;
  try {
    cachedDocs = raw ? (JSON.parse(raw) as SavedDocRef[]) : EMPTY;
  } catch {
    cachedDocs = EMPTY;
  }
  cachedRaw = raw;
  return cachedDocs;
}

function getServerSnapshot(): SavedDocRef[] {
  return EMPTY;
}

function subscribe(callback: () => void): () => void {
  internalSubscribers.add(callback);

  function handleStorage(e: StorageEvent) {
    if (e.key === STORAGE_KEY || e.key === null) {
      callback();
    }
  }

  window.addEventListener('storage', handleStorage);

  return () => {
    internalSubscribers.delete(callback);
    window.removeEventListener('storage', handleStorage);
  };
}

// ---------------------------------------------------------------------------
// Public React hook
// ---------------------------------------------------------------------------

export function useSavedDocs(): SavedDocRef[] {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

// ---------------------------------------------------------------------------
// Imperative API (unchanged from original)
// ---------------------------------------------------------------------------

export function listSavedDocs(): SavedDocRef[] {
  return read();
}

export function addSavedDoc(ref: SavedDocRef): void {
  const existing = read().filter((d) => d.id !== ref.id);
  write([ref, ...existing]);
}

export function removeSavedDoc(id: string): void {
  write(read().filter((d) => d.id !== id));
}

export function clearSavedDocs(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(STORAGE_KEY);
  notifySubscribers();
}
