'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { register } from '@/lib/auth';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await register(email, password);
      router.push('/desk');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm space-y-8">
      <div className="flex justify-center">
        <Link href="/">
          <Image
            src="/brand/wordmark.png"
            alt="Draftwell"
            width={461}
            height={113}
            className="h-8 w-auto"
          />
        </Link>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label
            htmlFor="email"
            className="font-sans text-xs uppercase tracking-widest text-stone-500"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-md border border-stone-300 bg-white px-3 py-2 font-sans text-sm text-ink placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-gold focus:ring-offset-1"
            placeholder="you@example.com"
          />
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="password"
            className="font-sans text-xs uppercase tracking-widest text-stone-500"
          >
            Password
            <span className="ml-1 normal-case text-stone-400">(8+ characters)</span>
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-stone-300 bg-white px-3 py-2 font-sans text-sm text-ink placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-gold focus:ring-offset-1"
            placeholder="••••••••"
          />
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="confirm"
            className="font-sans text-xs uppercase tracking-widest text-stone-500"
          >
            Confirm password
          </label>
          <input
            id="confirm"
            type="password"
            required
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full rounded-md border border-stone-300 bg-white px-3 py-2 font-sans text-sm text-ink placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-gold focus:ring-offset-1"
            placeholder="••••••••"
          />
        </div>

        {error && (
          <p role="alert" className="font-sans text-sm text-red-600">
            {error}
          </p>
        )}

        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Creating account…' : 'Create account'}
        </Button>
      </form>

      <p className="text-center font-sans text-sm text-stone-500">
        Already have an account?{' '}
        <Link
          href="/login"
          className="text-ink underline decoration-stone-300 underline-offset-4 hover:decoration-gold transition-colors"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
