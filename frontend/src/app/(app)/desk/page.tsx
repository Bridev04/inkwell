'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { TypewriterStream } from '@/components/typewriter-stream';
import { SectionLabel, BodyProse, Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';
import {
  submitFeedback,
  streamRewrite,
  submitGrammar,
  streamParaphrase,
  type FeedbackResponse,
  type GrammarResponse,
  type RewriteStyle,
  type ParaphraseMode,
  type RewriteDocumentEvent,
  type ParaphraseDocumentEvent,
} from '@/lib/api';
import { addSavedDoc } from '@/lib/savedDocs';
import { useDraftPersistence } from '@/lib/useDraftPersistence';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ActiveTool = 'feedback' | 'tone' | 'rewrite' | 'grammar' | 'paraphrase' | null;

const REWRITE_STYLES: { value: RewriteStyle; label: string }[] = [
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Casual' },
  { value: 'persuasive', label: 'Persuasive' },
  { value: 'concise', label: 'Concise' },
  { value: 'vivid', label: 'Vivid' },
];

const PARAPHRASE_MODES: { value: ParaphraseMode; label: string }[] = [
  { value: 'standard', label: 'Standard' },
  { value: 'simpler', label: 'Simpler' },
  { value: 'shorter', label: 'Shorter' },
  { value: 'academic', label: 'Academic' },
  { value: 'creative', label: 'Creative' },
];

const SCORE_LABEL_COLOR: Record<string, string> = {
  Great: 'text-green-700',
  Good: 'text-ink',
  Fair: 'text-amber-700',
  'Needs work': 'text-red-700',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

function readingTime(words: number): number {
  return Math.max(1, Math.ceil(words / 200));
}

function errorMsg(e: unknown): string {
  if (!(e instanceof Error)) return 'Something went wrong. Try again.';
  if (e.message.startsWith('HTTP 4'))
    return "The server couldn't process your draft. Check it isn't empty and try again.";
  if (e.message.startsWith('HTTP 5'))
    return 'The server ran into a problem. Try again in a moment.';
  return "Couldn't reach the server. Check your connection and try again.";
}

// ---------------------------------------------------------------------------
// Right panel sections
// ---------------------------------------------------------------------------

function FeedbackPanel({ result, savedId }: { result: FeedbackResponse; savedId?: string | null }) {
  const toneOnly = result.dimensions.length === 1 && result.dimensions[0]?.name === 'tone';

  return (
    <div className="space-y-5">
      {!toneOnly && (
        <div>
          <SectionLabel className="block mb-1">Editorial Feedback</SectionLabel>
          <Hairline variant="gold" className="mb-3" />
          <BodyProse className="text-sm">{result.overall_summary}</BodyProse>
        </div>
      )}

      {result.dimensions.map((dim) => (
        <div key={dim.name}>
          <SectionLabel as="h3" className="block mb-2 capitalize">
            {dim.name} · {dim.score}/5
          </SectionLabel>
          {dim.observations.length > 0 && (
            <ul className="space-y-1 mb-2">
              {dim.observations.map((obs, i) => (
                <li key={i}>
                  <BodyProse className="text-xs leading-relaxed">{obs}</BodyProse>
                </li>
              ))}
            </ul>
          )}
          {dim.suggestions.length > 0 && (
            <ul className="space-y-1 pl-3 border-l-2 border-stone-300">
              {dim.suggestions.map((sug, i) => (
                <li key={i}>
                  <BodyProse className="text-xs leading-relaxed text-stone-500">{sug}</BodyProse>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}

      {savedId && (
        <Mono className="block text-xs">
          Saved ·{' '}
          <Link href={`/documents/${savedId}`} className="underline hover:decoration-gold">
            {savedId.slice(0, 8)}…
          </Link>
        </Mono>
      )}
    </div>
  );
}

function GrammarPanel({
  result,
  savedId,
}: {
  result: GrammarResponse;
  savedId?: string | null;
}) {
  return (
    <div className="space-y-4">
      <SectionLabel className="block">Grammar Check</SectionLabel>
      <Hairline variant="gold" />

      <div className="flex items-center gap-2">
        <span className="font-sans text-xs text-stone-500">Overall:</span>
        <span className={`font-sans text-sm font-medium ${SCORE_LABEL_COLOR[result.scores.overall_label] ?? 'text-ink'}`}>
          {result.scores.overall_label}
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
                  {issue.category}
                </span>
                <div className="min-w-0">
                  <span className="font-sans text-xs line-through text-stone-500 mr-1">
                    {issue.original}
                  </span>
                  <span className="font-sans text-xs font-medium text-ink">
                    → {issue.replacement}
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

      {savedId && (
        <Mono className="block text-xs">
          Saved ·{' '}
          <Link href={`/documents/${savedId}`} className="underline hover:decoration-gold">
            {savedId.slice(0, 8)}…
          </Link>
        </Mono>
      )}
    </div>
  );
}

function StreamPanel({
  title,
  text,
  isStreaming,
  reducedMotion,
  savedId,
}: {
  title: string;
  text: string;
  isStreaming: boolean;
  reducedMotion: boolean;
  savedId?: string | null;
}) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionLabel className="block">{title}</SectionLabel>
        {!isStreaming && text && (
          <button
            onClick={handleCopy}
            className="font-sans text-xs text-stone-400 hover:text-ink transition-colors"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>
      <Hairline variant="gold" />
      <TypewriterStream fullText={text} isStreaming={isStreaming} reducedMotion={reducedMotion} />
      {!isStreaming && savedId && (
        <Mono className="block text-xs">
          Saved ·{' '}
          <Link href={`/documents/${savedId}`} className="underline hover:decoration-gold">
            {savedId.slice(0, 8)}…
          </Link>
        </Mono>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quick actions
// ---------------------------------------------------------------------------

function QuickActions({ onNew }: { onNew: () => void }) {
  return (
    <div className="space-y-3">
      <SectionLabel className="block">Quick Actions</SectionLabel>
      <Hairline />
      <div className="grid grid-cols-2 gap-2">
        <Button variant="secondary" size="sm" onClick={onNew} className="text-xs">
          New Draft
        </Button>
        <Link href="/documents">
          <Button variant="secondary" size="sm" className="text-xs w-full">
            Documents
          </Button>
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Writing Desk page
// ---------------------------------------------------------------------------

export default function DeskPage() {
  // Draft
  const [draft, setDraft, clearDraft] = useDraftPersistence('draftwell:desk-composer');
  const words = wordCount(draft);
  const readMin = readingTime(words);

  // Tool config
  const [rewriteStyle, setRewriteStyle] = useState<RewriteStyle>('formal');
  const [paraphraseMode, setParaphraseMode] = useState<ParaphraseMode>('standard');
  const [save, setSave] = useState(false);
  const [activeTool, setActiveTool] = useState<ActiveTool>(null);

  // Loading / error
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Feedback
  const [feedbackResult, setFeedbackResult] = useState<FeedbackResponse | null>(null);
  const [feedbackDocId, setFeedbackDocId] = useState<string | null>(null);

  // Rewrite
  const [rewriteText, setRewriteText] = useState('');
  const [isRewriteStreaming, setIsRewriteStreaming] = useState(false);
  const [rewriteDocId, setRewriteDocId] = useState<string | null>(null);

  // Grammar
  const [grammarResult, setGrammarResult] = useState<GrammarResponse | null>(null);
  const [grammarDocId, setGrammarDocId] = useState<string | null>(null);

  // Paraphrase
  const [paraphraseText, setParaphraseText] = useState('');
  const [isParaphraseStreaming, setIsParaphraseStreaming] = useState(false);
  const [paraphraseDocId, setParaphraseDocId] = useState<string | null>(null);

  // Accessibility
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }, []);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  function resetPanel() {
    setFeedbackResult(null);
    setFeedbackDocId(null);
    setRewriteText('');
    setRewriteDocId(null);
    setGrammarResult(null);
    setGrammarDocId(null);
    setParaphraseText('');
    setParaphraseDocId(null);
    setError(null);
  }

  async function handleFeedback() {
    if (!draft.trim()) return;
    resetPanel();
    setLoading(true);
    setActiveTool('feedback');
    try {
      const resp = await submitFeedback({ text: draft, save });
      setFeedbackResult(resp);
      if (save && resp.document_id) {
        setFeedbackDocId(resp.document_id);
        addSavedDoc({ id: resp.document_id, createdAt: new Date().toISOString(), snippet: draft.slice(0, 80) });
        clearDraft();
      }
    } catch (e) {
      setError(errorMsg(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleTone() {
    if (!draft.trim()) return;
    resetPanel();
    setLoading(true);
    setActiveTool('tone');
    try {
      const resp = await submitFeedback({ text: draft, focus: ['tone'], save });
      setFeedbackResult(resp);
      if (save && resp.document_id) {
        setFeedbackDocId(resp.document_id);
        addSavedDoc({ id: resp.document_id, createdAt: new Date().toISOString(), snippet: draft.slice(0, 80) });
      }
    } catch (e) {
      setError(errorMsg(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleRewrite() {
    if (!draft.trim()) return;
    resetPanel();
    setLoading(true);
    setIsRewriteStreaming(true);
    setActiveTool('rewrite');
    try {
      await streamRewrite(
        { text: draft, style: rewriteStyle, save },
        {
          onToken: (evt) => setRewriteText((t) => t + evt.text),
          onDone: () => {},
          onError: (evt) => setError(evt.message),
          onDocument: (evt: RewriteDocumentEvent) => {
            setRewriteDocId(evt.document_id);
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
      setIsRewriteStreaming(false);
      setLoading(false);
    }
  }

  async function handleGrammar() {
    if (!draft.trim()) return;
    resetPanel();
    setLoading(true);
    setActiveTool('grammar');
    try {
      const resp = await submitGrammar({ text: draft, save });
      setGrammarResult(resp);
      if (save && resp.document_id) {
        setGrammarDocId(resp.document_id);
        addSavedDoc({ id: resp.document_id, createdAt: new Date().toISOString(), snippet: draft.slice(0, 80) });
        clearDraft();
      }
    } catch (e) {
      setError(errorMsg(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleParaphrase() {
    if (!draft.trim()) return;
    resetPanel();
    setLoading(true);
    setIsParaphraseStreaming(true);
    setActiveTool('paraphrase');
    try {
      await streamParaphrase(
        { text: draft, mode: paraphraseMode, save },
        {
          onToken: (evt) => setParaphraseText((t) => t + evt.text),
          onDone: () => {},
          onError: (evt) => setError(evt.message),
          onDocument: (evt: ParaphraseDocumentEvent) => {
            setParaphraseDocId(evt.document_id);
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
      setIsParaphraseStreaming(false);
      setLoading(false);
    }
  }

  const isStreaming = isRewriteStreaming || isParaphraseStreaming;
  const isBusy = loading || isStreaming;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <>
      {/* Skip link */}
      <a
        href="#desk-textarea"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-cream focus:border focus:border-gold focus:rounded-md focus:px-4 focus:py-2 focus:font-sans focus:text-sm focus:text-ink"
      >
        Skip to editor
      </a>

      <div className="flex flex-1 overflow-hidden">
        {/* ---------------------------------------------------------------- */}
        {/* Main editor column                                                */}
        {/* ---------------------------------------------------------------- */}
        <main className="flex-1 overflow-y-auto">
          <div className="px-8 py-8 max-w-3xl">
            {/* Page heading */}
            <div className="mb-6">
              <h1 className="font-serif text-2xl font-semibold text-ink-strong">Writing Desk</h1>
              <p className="font-sans text-sm text-stone-500 mt-0.5">
                Refine your draft with thoughtful AI feedback.
              </p>
            </div>

            {/* Metadata bar */}
            <div className="flex items-center gap-3 mb-4">
              <Mono className="text-[0.625rem] uppercase tracking-widest text-stone-500">
                Current Draft
              </Mono>
              <span className="text-stone-300">·</span>
              <Mono className="text-[0.625rem] text-stone-500">Words: {words}</Mono>
              <span className="text-stone-300">·</span>
              <Mono className="text-[0.625rem] text-stone-500">
                Reading Time: {readMin} min
              </Mono>
            </div>

            {/* Editor */}
            <Textarea
              id="desk-textarea"
              placeholder="Paste or type your draft here…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="min-h-[320px] font-serif text-base leading-relaxed"
              aria-label="Your draft"
            />

            {/* Controls */}
            <div className="flex flex-col gap-3 mt-4">
              {/* Row 1: direct-action tools + save toggle */}
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  onClick={handleFeedback}
                  disabled={isBusy || !draft.trim()}
                  className="text-xs"
                >
                  {loading && activeTool === 'feedback' ? 'Analyzing…' : 'Get Feedback'}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleGrammar}
                  disabled={isBusy || !draft.trim()}
                  className="text-xs"
                >
                  {loading && activeTool === 'grammar' ? 'Checking…' : 'Check Grammar'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTone}
                  disabled={isBusy || !draft.trim()}
                  className="text-xs"
                >
                  {loading && activeTool === 'tone' ? 'Analyzing…' : 'Analyze Tone'}
                </Button>
                <label className="flex items-center gap-2 cursor-pointer ml-auto" htmlFor="desk-save-switch">
                  <Switch id="desk-save-switch" checked={save} onCheckedChange={setSave} size="sm" />
                  <SectionLabel as="span">Save</SectionLabel>
                </label>
              </div>

              {/* Row 2: split-button tools paired with their mode selector */}
              <div className="flex flex-wrap items-stretch gap-2">
                <div className="flex items-stretch rounded-md border border-stone-300 overflow-hidden">
                  <button
                    onClick={handleRewrite}
                    disabled={isBusy || !draft.trim()}
                    className="px-3 font-sans text-[0.8rem] text-ink border-r border-stone-300 hover:bg-stone-300/20 transition-colors disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap"
                  >
                    {isRewriteStreaming ? 'Writing…' : 'Rewrite'}
                  </button>
                  <select
                    value={rewriteStyle}
                    onChange={(e) => setRewriteStyle(e.target.value as RewriteStyle)}
                    disabled={isBusy}
                    aria-label="Rewrite style"
                    className="px-2 font-sans text-xs text-stone-500 bg-cream focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-gold disabled:opacity-50"
                  >
                    {REWRITE_STYLES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-stretch rounded-md border border-stone-300 overflow-hidden">
                  <button
                    onClick={handleParaphrase}
                    disabled={isBusy || !draft.trim()}
                    className="px-3 font-sans text-[0.8rem] text-ink border-r border-stone-300 hover:bg-stone-300/20 transition-colors disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap"
                  >
                    {isParaphraseStreaming ? 'Paraphrasing…' : 'Paraphrase'}
                  </button>
                  <select
                    value={paraphraseMode}
                    onChange={(e) => setParaphraseMode(e.target.value as ParaphraseMode)}
                    disabled={isBusy}
                    aria-label="Paraphrase mode"
                    className="px-2 font-sans text-xs text-stone-500 bg-cream focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-gold disabled:opacity-50"
                  >
                    {PARAPHRASE_MODES.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Error state */}
            {error && (
              <div className="mt-4 flex items-center gap-2">
                <SectionLabel className="text-stone-500">{error}</SectionLabel>
              </div>
            )}
          </div>
        </main>

        {/* ---------------------------------------------------------------- */}
        {/* Right panel                                                        */}
        {/* ---------------------------------------------------------------- */}
        <aside
          className="w-[38%] min-w-[340px] max-w-[480px] shrink-0 border-l border-stone-300 overflow-y-auto bg-cream"
          aria-label="Results panel"
          aria-live="polite"
          aria-busy={isBusy}
        >
          <div className="p-6 space-y-8">
            {/* Empty state */}
            {!activeTool && !error && (
              <p className="font-sans text-sm text-stone-400 leading-relaxed text-center py-6">
                Run a tool to see results here.
              </p>
            )}

            {/* Feedback / Tone results */}
            {activeTool && (activeTool === 'feedback' || activeTool === 'tone') && (
              <div>
                {loading && !feedbackResult && (
                  <Mono className="text-stone-500 text-xs">Analyzing…</Mono>
                )}
                {feedbackResult && (
                  <FeedbackPanel result={feedbackResult} savedId={feedbackDocId} />
                )}
              </div>
            )}

            {/* Rewrite result */}
            {activeTool === 'rewrite' && (
              <StreamPanel
                title="Rewrite"
                text={rewriteText}
                isStreaming={isRewriteStreaming}
                reducedMotion={reducedMotion}
                savedId={rewriteDocId}
              />
            )}

            {/* Grammar result */}
            {activeTool === 'grammar' && (
              <div>
                {loading && !grammarResult && (
                  <Mono className="text-stone-500 text-xs">Checking grammar…</Mono>
                )}
                {grammarResult && (
                  <GrammarPanel result={grammarResult} savedId={grammarDocId} />
                )}
              </div>
            )}

            {/* Paraphrase result */}
            {activeTool === 'paraphrase' && (
              <StreamPanel
                title="Paraphrase"
                text={paraphraseText}
                isStreaming={isParaphraseStreaming}
                reducedMotion={reducedMotion}
                savedId={paraphraseDocId}
              />
            )}

            {/* Quick actions — always visible */}
            <QuickActions onNew={clearDraft} />
          </div>
        </aside>
      </div>
    </>
  );
}
