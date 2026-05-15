'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { SectionLabel, BodyProse, Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';
import { submitGrammar, type GrammarResponse } from '@/lib/api';
import { addSavedDoc } from '@/lib/savedDocs';
import { useDraftPersistence } from '@/lib/useDraftPersistence';

const QUALITY_COLOR: Record<string, string> = {
  Excellent: 'text-green-700',
  Good: 'text-ink',
  Fair: 'text-amber-700',
  Poor: 'text-red-700',
};

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
            <Button variant="secondary" size="sm" onClick={() => { setDraft(''); setResult(null); setSavedId(null); setError(null); }} className="text-xs">
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

      {/* Results panel */}
      <aside
        className="w-80 shrink-0 border-l border-stone-300 overflow-y-auto bg-cream"
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
                <SectionLabel className="block mb-1">Grammar Check</SectionLabel>
                <Hairline variant="gold" className="mb-3" />
              </div>

              <div className="flex items-center gap-2">
                <span className="font-sans text-xs text-stone-500">Quality:</span>
                <span className={`font-sans text-sm font-medium ${QUALITY_COLOR[result.overall_quality] ?? 'text-ink'}`}>
                  {result.overall_quality}
                </span>
                <span className="font-sans text-xs text-stone-500 ml-auto">
                  {result.issues.length} issue{result.issues.length !== 1 ? 's' : ''}
                </span>
              </div>

              {result.issues.length === 0 ? (
                <BodyProse className="text-sm text-stone-500">No issues found. Great writing!</BodyProse>
              ) : (
                <ul className="space-y-3">
                  {result.issues.map((issue, i) => (
                    <li key={i} className="border border-stone-300 rounded-md p-3 space-y-1">
                      <div className="flex items-start gap-2">
                        <span className="font-mono text-[0.625rem] uppercase tracking-wide text-stone-500 mt-0.5 shrink-0">
                          {issue.type}
                        </span>
                        <div className="min-w-0">
                          <span className="font-sans text-xs line-through text-stone-500 mr-1">
                            {issue.original}
                          </span>
                          <span className="font-sans text-xs font-medium text-ink">
                            → {issue.suggestion}
                          </span>
                        </div>
                      </div>
                      <BodyProse className="text-xs text-stone-500 leading-relaxed">
                        {issue.explanation}
                      </BodyProse>
                    </li>
                  ))}
                </ul>
              )}

              {result.issues.length > 0 && (
                <button
                  onClick={() => setShowCorrected((v) => !v)}
                  className="font-sans text-xs text-ink underline decoration-stone-300 underline-offset-4 hover:decoration-gold transition-colors"
                >
                  {showCorrected ? 'Hide corrected text' : 'Show corrected text'}
                </button>
              )}

              {showCorrected && (
                <div className="border border-stone-300 rounded-md p-4 bg-stone-300/10">
                  <BodyProse className="text-sm whitespace-pre-wrap">{result.corrected_text}</BodyProse>
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
            <BodyProse className="text-sm text-stone-400">
              Results will appear here after you check your draft.
            </BodyProse>
          )}
        </div>
      </aside>
    </div>
  );
}
