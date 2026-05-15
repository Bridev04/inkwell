'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { SectionLabel, Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';
import { submitGrammar, type GrammarResponse, type GrammarIssue } from '@/lib/api';
import { addSavedDoc } from '@/lib/savedDocs';
import { useDraftPersistence } from '@/lib/useDraftPersistence';

const QUALITY_COLOR: Record<string, string> = {
  Excellent: 'text-green-700',
  Good: 'text-ink',
  Fair: 'text-amber-700',
  Poor: 'text-red-700',
};

const QUALITY_BG: Record<string, string> = {
  Excellent: 'bg-green-50 border-green-200',
  Good: 'bg-stone-50 border-stone-200',
  Fair: 'bg-amber-50 border-amber-200',
  Poor: 'bg-red-50 border-red-200',
};

function typeStyles(type: string): { badge: string; accent: string } {
  const t = type.toLowerCase();
  if (t === 'spelling')    return { badge: 'bg-red-100 text-red-700',    accent: 'border-l-red-400' };
  if (t === 'grammar')     return { badge: 'bg-amber-100 text-amber-700', accent: 'border-l-amber-400' };
  if (t === 'punctuation') return { badge: 'bg-blue-100 text-blue-700',   accent: 'border-l-blue-400' };
  if (t === 'style')       return { badge: 'bg-purple-100 text-purple-700', accent: 'border-l-purple-400' };
  return                          { badge: 'bg-stone-100 text-stone-600', accent: 'border-l-stone-400' };
}

function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

function errorMsg(e: unknown): string {
  if (!(e instanceof Error)) return 'Something went wrong. Try again.';
  if (e.message.startsWith('HTTP 4'))
    return "The server couldn't process your draft. Check it isn't empty and try again.";
  if (e.message.startsWith('HTTP 5'))
    return 'The server ran into a problem. Try again in a moment.';
  return "Couldn't reach the server. Check your connection and try again.";
}

function IssueCard({ issue }: { issue: GrammarIssue }) {
  const { badge, accent } = typeStyles(issue.type);
  return (
    <li className={`rounded-lg border border-stone-200 border-l-4 ${accent} bg-cream/80 p-4 space-y-2`}>
      <span className={`inline-block text-[0.6rem] font-mono uppercase tracking-widest px-1.5 py-0.5 rounded ${badge}`}>
        {issue.type}
      </span>
      <div className="flex items-baseline flex-wrap gap-x-2 gap-y-0.5">
        <span className="font-sans text-sm line-through text-stone-400">{issue.original}</span>
        <span className="font-sans text-stone-400 text-xs">→</span>
        <span className="font-sans text-sm font-semibold text-ink">{issue.suggestion}</span>
      </div>
      <p className="font-sans text-xs text-stone-500 leading-relaxed">{issue.explanation}</p>
    </li>
  );
}

export default function GrammarPage() {
  const [draft, setDraft, clearDraft] = useDraftPersistence('draftwell:grammar-composer');
  const words = wordCount(draft);

  const [save, setSave] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GrammarResponse | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [showCorrected, setShowCorrected] = useState(false);

  async function handleCheck() {
    if (!draft.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setSavedId(null);
    setShowCorrected(false);
    try {
      const resp = await submitGrammar({ text: draft, save });
      setResult(resp);
      if (save && resp.document_id) {
        setSavedId(resp.document_id);
        addSavedDoc({ id: resp.document_id, createdAt: new Date().toISOString(), snippet: draft.slice(0, 80) });
        clearDraft();
      }
    } catch (e) {
      setError(errorMsg(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Editor column */}
      <main className="flex-1 overflow-y-auto">
        <div className="px-8 py-8 max-w-3xl">
          <div className="mb-6">
            <h1 className="font-serif text-2xl font-semibold text-ink-strong">Grammar Check</h1>
            <p className="font-sans text-sm text-stone-500 mt-0.5">
              Find and fix grammar, spelling, and punctuation issues.
            </p>
          </div>

          <div className="flex items-center gap-3 mb-4">
            <Mono className="text-[0.625rem] uppercase tracking-widest text-stone-500">Draft</Mono>
            <span className="text-stone-300">·</span>
            <Mono className="text-[0.625rem] text-stone-500">Words: {words}</Mono>
          </div>

          <Textarea
            placeholder="Paste or type your draft here…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="min-h-[320px] font-serif text-base leading-relaxed"
            aria-label="Your draft"
          />

          <div className="flex items-center gap-4 mt-4">
            <label className="flex items-center gap-2 cursor-pointer" htmlFor="grammar-save-switch">
              <Switch id="grammar-save-switch" checked={save} onCheckedChange={setSave} size="sm" />
              <SectionLabel as="span">Save draft</SectionLabel>
            </label>
          </div>

          <div className="flex gap-2 mt-5">
            <Button size="sm" onClick={handleCheck} disabled={loading || !draft.trim()} className="text-xs">
              {loading ? 'Checking…' : 'Check Grammar'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => { setDraft(''); setResult(null); setSavedId(null); setError(null); }}
              className="text-xs"
            >
              Clear
            </Button>
          </div>

          {error && (
            <div className="mt-4">
              <SectionLabel className="text-stone-500">{error}</SectionLabel>
            </div>
          )}
        </div>
      </main>

      {/* Results panel — auto-width between 340–480px */}
      <aside
        className="w-[38%] min-w-[340px] max-w-[480px] shrink-0 border-l border-stone-300 overflow-y-auto bg-cream"
        aria-label="Grammar results"
        aria-live="polite"
        aria-busy={loading}
      >
        <div className="p-6 space-y-5">
          {loading && (
            <Mono className="text-stone-500 text-xs">Checking grammar…</Mono>
          )}

          {result && (
            <>
              <div>
                <SectionLabel className="block mb-1">Results</SectionLabel>
                <Hairline variant="gold" className="mb-4" />
              </div>

              {/* Quality badge */}
              <div className={`flex items-center justify-between rounded-lg border px-4 py-3 ${QUALITY_BG[result.overall_quality] ?? 'bg-stone-50 border-stone-200'}`}>
                <div>
                  <p className="font-sans text-[0.6rem] uppercase tracking-widest text-stone-500 mb-0.5">Overall Quality</p>
                  <p className={`font-sans text-base font-semibold ${QUALITY_COLOR[result.overall_quality] ?? 'text-ink'}`}>
                    {result.overall_quality}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-sans text-[0.6rem] uppercase tracking-widest text-stone-500 mb-0.5">Issues Found</p>
                  <p className="font-sans text-base font-semibold text-ink">{result.issues.length}</p>
                </div>
              </div>

              {result.issues.length === 0 ? (
                <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3">
                  <p className="font-sans text-sm text-green-700">No issues found. Great writing!</p>
                </div>
              ) : (
                <ul className="space-y-3">
                  {result.issues.map((issue, i) => (
                    <IssueCard key={i} issue={issue} />
                  ))}
                </ul>
              )}

              {result.issues.length > 0 && (
                <>
                  <Hairline />
                  <button
                    onClick={() => setShowCorrected((v) => !v)}
                    className="font-sans text-xs text-ink underline decoration-stone-300 underline-offset-4 hover:decoration-gold transition-colors"
                  >
                    {showCorrected ? 'Hide corrected text' : 'Show corrected text'}
                  </button>
                </>
              )}

              {showCorrected && (
                <div className="rounded-lg border border-stone-200 p-4 bg-stone-50">
                  <p className="font-sans text-xs uppercase tracking-widest text-stone-400 mb-3">Corrected</p>
                  <p className="font-sans text-sm leading-relaxed text-ink whitespace-pre-wrap">{result.corrected_text}</p>
                </div>
              )}

              {savedId && (
                <Mono className="block text-xs">
                  Saved ·{' '}
                  <Link href={`/documents/${savedId}`} className="underline hover:decoration-gold">
                    {savedId.slice(0, 8)}…
                  </Link>
                </Mono>
              )}
            </>
          )}

          {!loading && !result && (
            <p className="font-sans text-sm text-stone-400 leading-relaxed">
              Results will appear here after you check your draft.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}
