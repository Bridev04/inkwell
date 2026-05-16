'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { TypewriterStream } from '@/components/typewriter-stream';
import { SectionLabel, Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';
import {
  streamParaphrase,
  type ParaphraseMode,
  type ParaphraseDocumentEvent,
} from '@/lib/api';
import { addSavedDoc } from '@/lib/savedDocs';
import { useDraftPersistence } from '@/lib/useDraftPersistence';

const WORD_LIMIT = 150;

const PARAPHRASE_MODES: { value: ParaphraseMode; label: string; description: string }[] = [
  { value: 'standard', label: 'Standard',  description: 'Rephrase while keeping the original meaning' },
  { value: 'simpler',  label: 'Simpler',   description: 'Use plainer language and shorter sentences' },
  { value: 'shorter',  label: 'Shorter',   description: 'Cut to the core idea' },
  { value: 'academic', label: 'Academic',  description: 'Formal, scholarly tone' },
  { value: 'creative', label: 'Creative',  description: 'More expressive and varied phrasing' },
];

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

export default function ParaphrasePage() {
  const [draft, setDraft, clearDraft] = useDraftPersistence('draftwell:paraphrase-composer');
  const words = wordCount(draft);
  const overLimit = words > WORD_LIMIT;

  const [mode, setMode] = useState<ParaphraseMode>('standard');
  const [save, setSave] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outputText, setOutputText] = useState('');
  const [savedId, setSavedId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [reducedMotion] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false
  );

  function handleCopy() {
    if (!outputText) return;
    navigator.clipboard.writeText(outputText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleParaphrase() {
    if (!draft.trim() || overLimit) return;
    setLoading(true);
    setIsStreaming(true);
    setError(null);
    setOutputText('');
    setSavedId(null);
    try {
      await streamParaphrase(
        { text: draft, mode, save },
        {
          onToken: (evt) => setOutputText((t) => t + evt.text),
          onDone: () => {},
          onError: (evt) => setError(evt.message),
          onDocument: (evt: ParaphraseDocumentEvent) => {
            setSavedId(evt.document_id);
            if (save) {
              addSavedDoc({ id: evt.document_id, createdAt: new Date().toISOString(), snippet: draft.slice(0, 80) });
              clearDraft();
            }
          },
        }
      );
    } catch (e) {
      setError(errorMsg(e));
    } finally {
      setIsStreaming(false);
      setLoading(false);
    }
  }

  const isBusy = loading || isStreaming;

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Editor column */}
      <main className="flex-1 overflow-y-auto">
        <div className="px-8 py-8 max-w-3xl">
          <div className="mb-6">
            <h1 className="font-serif text-2xl font-semibold text-ink-strong">Paraphrase</h1>
            <p className="font-sans text-sm text-stone-500 mt-0.5">
              Rephrase your draft in a different style or tone.
            </p>
          </div>

          {/* Word count bar */}
          <div className="flex items-center gap-3 mb-4">
            <Mono className="text-[0.625rem] uppercase tracking-widest text-stone-500">Draft</Mono>
            <span className="text-stone-300">·</span>
            <Mono className={`text-[0.625rem] tabular-nums ${overLimit ? 'text-red-600 font-semibold' : 'text-stone-500'}`}>
              {words} / {WORD_LIMIT} words
            </Mono>
            {overLimit && (
              <span className="font-sans text-[0.625rem] text-red-600">— trim to {WORD_LIMIT} words or fewer</span>
            )}
          </div>

          <Textarea
            placeholder="Paste or type your draft here…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className={`min-h-[320px] font-serif text-base leading-relaxed ${overLimit ? 'border-red-300 focus-visible:ring-red-400' : ''}`}
            aria-label="Your draft"
          />

          {/* Mode selector */}
          <div className="mt-4">
            <SectionLabel className="block mb-2">Mode</SectionLabel>
            <div className="flex flex-wrap gap-2">
              {PARAPHRASE_MODES.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMode(m.value)}
                  title={m.description}
                  className={[
                    'px-3 py-1.5 rounded-md font-sans text-xs transition-colors duration-150 border',
                    mode === m.value
                      ? 'bg-ink text-cream border-ink'
                      : 'bg-cream text-stone-500 border-stone-300 hover:text-ink hover:border-stone-400',
                  ].join(' ')}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4 mt-4">
            <label className="flex items-center gap-2 cursor-pointer" htmlFor="paraphrase-save-switch">
              <Switch id="paraphrase-save-switch" checked={save} onCheckedChange={setSave} size="sm" />
              <SectionLabel as="span">Save draft</SectionLabel>
            </label>
          </div>

          <div className="flex gap-2 mt-5">
            <Button
              size="sm"
              onClick={handleParaphrase}
              disabled={isBusy || !draft.trim() || overLimit}
              className="text-xs"
            >
              {isStreaming ? 'Paraphrasing…' : 'Paraphrase'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => { setDraft(''); setOutputText(''); setSavedId(null); setError(null); }}
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
        aria-label="Paraphrase result"
        aria-live="polite"
        aria-busy={isBusy}
      >
        <div className="p-6 space-y-5">
          {(outputText || isStreaming) ? (
            <>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <SectionLabel className="block">
                    {PARAPHRASE_MODES.find((m) => m.value === mode)?.label ?? 'Paraphrase'}
                  </SectionLabel>
                  {!isStreaming && outputText && (
                    <button
                      onClick={handleCopy}
                      className="font-sans text-xs text-stone-400 hover:text-ink transition-colors"
                    >
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  )}
                </div>
                <Hairline variant="gold" className="mb-3" />
              </div>
              <TypewriterStream
                fullText={outputText}
                isStreaming={isStreaming}
                reducedMotion={reducedMotion}
                className="font-sans text-sm leading-7 text-ink max-w-prose"
              />
              {!isStreaming && savedId && (
                <Mono className="block text-xs">
                  Saved ·{' '}
                  <Link href={`/documents/${savedId}`} className="underline hover:decoration-gold">
                    {savedId.slice(0, 8)}…
                  </Link>
                </Mono>
              )}
            </>
          ) : (
            <p className="font-sans text-sm text-stone-400 leading-relaxed">
              Your paraphrased text will appear here.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}
