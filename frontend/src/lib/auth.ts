export interface UserRead {
  id: string;
  email: string;
  created_at: string;
}

function baseUrl(): string {
  if (typeof window !== 'undefined') return '';
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
}

async function throwIfNotOk(res: Response): Promise<void> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
}

export async function register(email: string, password: string): Promise<UserRead> {
  const res = await fetch(`${baseUrl()}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  await throwIfNotOk(res);
  return res.json() as Promise<UserRead>;
}

export async function login(email: string, password: string): Promise<UserRead> {
  const res = await fetch(`${baseUrl()}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  await throwIfNotOk(res);
  return res.json() as Promise<UserRead>;
}

export async function logout(): Promise<void> {
  await fetch(`${baseUrl()}/api/v1/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
}

export function googleSignInUrl(next = '/desk'): string {
  return `/api/v1/auth/google?next=${encodeURIComponent(next)}`;
}

export async function getMe(): Promise<UserRead | null> {
  const res = await fetch(`${baseUrl()}/api/v1/auth/me`, {
    credentials: 'include',
  });
  if (!res.ok) return null;
  return res.json() as Promise<UserRead>;
}
