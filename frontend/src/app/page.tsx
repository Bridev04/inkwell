'use client';

import { useState, useEffect } from 'react';

const REWRITE_STYLES = [
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Casual' },
  { value: 'persuasive', label: 'Persuasive' },
  { value: 'concise', label: 'Concise' },
  { value: 'vivid', label: 'Vivid' },
] as const;
import Image from 'next/image';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { SiteFooter } from '@/components/site-footer';
import { TypewriterStream } from '@/components/typewriter-stream';
import {
  DisplayHeading,
  SectionLabel,
  BodyProse,
  Mono,
} from '@/components/typography';
import { Hairline } from '@/components/hairline';
import {
  submitFeedback,
  streamRewrite,
  type FeedbackResponse,
  type RewriteStyle,
  type RewriteDocumentEvent,
} from '@/lib/api';
import { addSavedDoc } from '@/lib/savedDocs';
import { useDraftPersistence } from '@/lib/useDraftPersistence';

type Action = 'feedback' | 'rewrite' | null;

function errorMessage(e: unknown, context: 'feedback' | 'rewrite'): string {
  if (!(e instanceof Error)) return 'Something went wrong. Try again.';
  if (e.message.startsWith('HTTP 4'))
    return `The server couldn't process your draft. Check it isn't empty and try again.`;
  if (e.message.startsWith('HTTP 5'))
    return `The server ran into a problem${context === 'rewrite' ? ' while writing' : ''}. Try again in a moment.`;
  return `Couldn't reach the server. Check your connection and try again.`;
}

export default function Home() {
  const [draft, setDraft, clearDraft] = useDraftPersistence('draftwell:home-composer');
  const [style, setStyle] = useState<RewriteStyle>('formal');
  const [save, setSave] = useState(false);

  const [action, setAction] = useState<Action>(null);
  const [feedbackResult, setFeedbackResult] = useState<FeedbackResponse | null>(null);
  const [rewriteText, setRewriteText] = useState('');
  const [rewriteDocumentId, setRewriteDocumentId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReducedMotion(
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }, []);

  async function handleFeedback() {
    if (!draft.trim()) return;
    setLoading(true);
    setIsStreaming(false);
    setError(null);
    setFeedbackResult(null);
    setRewriteText('');
    setRewriteDocumentId(null);
    setAction('feedback');
    try {
      const resp = await submitFeedback({ text: draft, save });
      setFeedbackResult(resp);
      if (save && resp.document_id) {
        addSavedDoc({
          id: resp.document_id,
          createdAt: new Date().toISOString(),
          snippet: draft.slice(0, 80),
        });
        clearDraft();
      }
    } catch (e) {
      setError(errorMessage(e, 'feedback'));
    } finally {
      setLoading(false);
    }
  }

  async function handleRewrite() {
    if (!draft.trim()) return;
    setLoading(true);
    setIsStreaming(true);
    setError(null);
    setFeedbackResult(null);
    setRewriteText('');
    setRewriteDocumentId(null);
    setAction('rewrite');
    try {
      await streamRewrite(
        { text: draft, style, save },
        {
          onToken: (evt) => setRewriteText((t) => t + evt.text),
          onDone: () => {},
          onError: (evt) => setError(evt.message),
          onDocument: (evt: RewriteDocumentEvent) => {
            setRewriteDocumentId(evt.document_id);
            if (save) {
              addSavedDoc({
                id: evt.document_id,
                createdAt: new Date().toISOString(),
                snippet: draft.slice(0, 80),
              });
              clearDraft();
            }
          },
        }
      );
    } catch (e) {
      setError(errorMessage(e, 'rewrite'));
    } finally {
      setIsStreaming(false);
      setLoading(false);
    }
  }

  return (
    <>
      {/* Skip link — first focusable element on the page */}
      <a
        href="#composer-textarea"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-cream focus:border focus:border-gold focus:rounded-md focus:px-4 focus:py-2 focus:font-sans focus:text-sm focus:text-ink"
      >
        Skip to composer
      </a>

      {/* Hero */}
      <header className="min-h-[80vh] flex items-center justify-center px-6">
        <Image
          src="/brand/wordmark-vertical.png"
          alt="Draftwell — AI-powered writing assistant"
          width={686}
          height={473}
          className="w-full max-w-[480px] lg:max-w-[640px] h-auto"
          sizes="(min-width: 1024px) 640px, 480px"
          preload
        />
      </header>

      {/* Composer */}
      <main id="composer" className="w-full max-w-2xl mx-auto px-6 lg:px-10 pb-24">
        <DisplayHeading as="h1" className="mb-4">
          Bring your draft.
        </DisplayHeading>
        <BodyProse className="mb-8 text-stone-500">
          Paste anything. Get sharp feedback or a clean rewrite in the voice you choose.
        </BodyProse>

        <SectionLabel as="h2" className="mb-2 block">
          Your draft
        </SectionLabel>
        <Textarea
          id="composer-textarea"
          placeholder="Paste or type here."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="min-h-[280px]"
          aria-label="Your draft"
        />

        {/* Controls row */}
        <div className="flex flex-col sm:flex-row sm:items-end gap-4 mt-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="style-select">
              <SectionLabel>Rewrite style</SectionLabel>
            </label>
            <select
              id="style-select"
              value={style}
              onChange={(e) => setStyle(e.target.value as RewriteStyle)}
              className="bg-cream border border-stone-300 rounded-md px-3 py-2 font-sans text-sm text-ink focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-cream focus:outline-none"
            >
              {REWRITE_STYLES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-3 cursor-pointer" htmlFor="save-switch">
            <Switch
              id="save-switch"
              checked={save}
              onCheckedChange={setSave}
            />
            <SectionLabel as="span">Save this draft</SectionLabel>
          </label>
        </div>

        {/* Action row */}
        <div className="flex justify-end gap-3 mt-6">
          <Button
            variant="secondary"
            onClick={handleRewrite}
            disabled={loading || !draft.trim()}
            aria-label="Get rewrite"
          >
            Get rewrite
          </Button>
          <Button
            onClick={handleFeedback}
            disabled={loading || !draft.trim()}
          >
            {loading && action === 'feedback' ? 'Analyzing…' : 'Get feedback'}
          </Button>
        </div>

        <Hairline className="mt-6" />

        {/* Error state */}
        {error && (
          <div className="mt-4">
            <SectionLabel className="text-stone-500">{error}</SectionLabel>{' '}
            <button
              onClick={action === 'rewrite' ? handleRewrite : handleFeedback}
              className="font-sans text-[0.75rem] text-ink underline decoration-stone-300 underline-offset-4 hover:decoration-gold hover:text-ink-strong transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        {/* Saved drafts link */}
        <div className="flex justify-end mt-4">
          <Link
            href="/documents"
            className="font-mono text-stone-600 text-xs hover:text-ink transition-colors"
          >
            Saved drafts →
          </Link>
        </div>
      </main>

      {/* Result region */}
      {action === 'feedback' && (
        <section
          aria-live="polite"
          aria-busy={loading && action === 'feedback'}
          className="w-full max-w-2xl mx-auto px-6 lg:px-10 pb-24"
        >
          <DisplayHeading as="h2" variant="h2" className="mb-3">
            Feedback
          </DisplayHeading>
          <Hairline variant="gold" className="mb-6" />

          {loading && !feedbackResult && (
            <Mono className="text-stone-500">Analyzing…</Mono>
          )}

          {feedbackResult && (
            <div className="space-y-6">
              <BodyProse>{feedbackResult.overall_summary}</BodyProse>

              {feedbackResult.dimensions.map((dim) => (
                <div key={dim.name}>
                  <SectionLabel as="h3" className="mb-2 block">
                    {dim.name} · {dim.score}/10
                  </SectionLabel>
                  {dim.observations.length > 0 && (
                    <ul className="space-y-1 mb-2">
                      {dim.observations.map((obs, i) => (
                        <li key={i}>
                          <BodyProse className="text-sm">{obs}</BodyProse>
                        </li>
                      ))}
                    </ul>
                  )}
                  {dim.suggestions.length > 0 && (
                    <ul className="space-y-1 pl-4 border-l-2 border-stone-300">
                      {dim.suggestions.map((sug, i) => (
                        <li key={i}>
                          <BodyProse className="text-sm text-stone-500">{sug}</BodyProse>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}

              {feedbackResult.document_id && (
                <Mono className="block mt-4">
                  Saved ·{' '}
                  <Link
                    href={`/documents/${feedbackResult.document_id}`}
                    className="underline hover:decoration-gold"
                  >
                    {feedbackResult.document_id.slice(0, 8)}…
                  </Link>
                </Mono>
              )}
            </div>
          )}
        </section>
      )}

      {action === 'rewrite' && (
        <section
          aria-live="polite"
          aria-busy={isStreaming}
          className="w-full max-w-2xl mx-auto px-6 lg:px-10 pb-24"
        >
          <DisplayHeading as="h2" variant="h2" className="mb-3">
            Rewrite
          </DisplayHeading>
          <Hairline variant="gold" className="mb-6" />

          <TypewriterStream
            fullText={rewriteText}
            isStreaming={isStreaming}
            reducedMotion={reducedMotion}
          />

          {!isStreaming && rewriteDocumentId && (
            <Mono className="block mt-4">
              Saved ·{' '}
              <Link
                href={`/documents/${rewriteDocumentId}`}
                className="underline hover:decoration-gold"
              >
                {rewriteDocumentId.slice(0, 8)}…
              </Link>
            </Mono>
          )}
        </section>
      )}

      <SiteFooter />
    </>
  );
}
