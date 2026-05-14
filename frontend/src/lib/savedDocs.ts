const STORAGE_KEY = 'draftwell:saved-docs';

export interface SavedDocRef {
  id: string;
  createdAt: string;
  snippet: string;
}

function read(): SavedDocRef[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedDocRef[]) : [];
  } catch {
    return [];
  }
}

function write(docs: SavedDocRef[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(docs));
}

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
}
