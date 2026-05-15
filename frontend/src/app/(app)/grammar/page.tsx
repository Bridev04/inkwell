'use client';

import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { SectionLabel, Mono } from '@/components/typography';
import { submitGrammar, type GrammarResponse, type GrammarIssue, type GrammarScores } from '@/lib/api';
import { addSavedDoc } from '@/lib/savedDocs';
import { useDraftPersistence } from '@/lib/useDraftPersistence';

// ---------------------------------------------------------------------------
// Constants & scoring
// ---------------------------------------------------------------------------

const CATEGORY_STYLE: Record<string, { underline: string; activeBg: string; badge: string; dot: string }> = {
  grammar:     { underline: 'decoration-red-400',    activeBg: 'bg-red-50',    badge: 'bg-red-100 text-red-800',      dot: 'bg-red-400' },
  spelling:    { underline: 'decoration-orange-400', activeBg: 'bg-orange-50', badge: 'bg-orange-100 text-orange-800', dot: 'bg-orange-400' },
  punctuation: { underline: 'decoration-blue-400',   activeBg: 'bg-blue-50',   badge: 'bg-blue-100 text-blue-800',    dot: 'bg-blue-400' },
  style:       { underline: 'decoration-purple-400', activeBg: 'bg-purple-50', badge: 'bg-purple-100 text-purple-800', dot: 'bg-purple-400' },
};

// Mirrors the backend _compute_scores formula exactly.
// score = max(0, 100 - floor(count * penalty * 100 / wordCount))
// overall = min of all four categories
const _PENALTY: Record<string, number> = { grammar: 3, spelling: 4, punctuation: 2, style: 1 };

function computeScores(
  issues: GrammarIssue[],
  unresolvedSet: Set<number>,
  wordCount: number,
): GrammarScores {
  const wc = Math.max(wordCount, 1);
  const counts: Record<string, number> = { grammar: 0, spelling: 0, punctuation: 0, style: 0 };
  issues.forEach((issue, idx) => {
    if (unresolvedSet.has(idx)) counts[issue.category] = (counts[issue.category] ?? 0) + 1;
  });
  const score = (kind: string) =>
    Math.max(0, 100 - Math.floor((counts[kind] * _PENALTY[kind] * 100) / wc));
  const g = score('grammar');
  const s = score('spelling');
  const p = score('punctuation');
  const st = score('style');
  const overall = Math.min(g, s, p, st);
  const overall_label: GrammarScores['overall_label'] =
    overall >= 85 ? 'Great' : overall >= 70 ? 'Good' : overall >= 50 ? 'Fair' : 'Needs work';
  return { grammar: g, spelling: s, punctuation: p, style: st, overall, overall_label };
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

// ---------------------------------------------------------------------------
// Annotated editor: overlay of spans keyed to start/end offsets
// ---------------------------------------------------------------------------

type Segment =
  | { kind: 'text'; content: string }
  | { kind: 'issue'; content: string; issueIndex: number; category: string };

function buildSegments(text: string, issues: GrammarIssue[], visibleSet: Set<number>): Segment[] {
  const spans = issues
    .map((issue, idx) => {
      if (!visibleSet.has(idx)) return null;
      if (issue.start < 0 || issue.end > text.length) return null;
      if (text.slice(issue.start, issue.end) !== issue.original) return null;
      return { idx, pos: issue.start, end: issue.end, category: issue.category };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
    .sort((a, b) => a.pos - b.pos);

  const segs: Segment[] = [];
  let cursor = 0;
  for (const item of spans) {
    if (item.pos < cursor) continue;
    if (item.pos > cursor) segs.push({ kind: 'text', content: text.slice(cursor, item.pos) });
    segs.push({ kind: 'issue', content: text.slice(item.pos, item.end), issueIndex: item.idx, category: item.category });
    cursor = item.end;
  }
  if (cursor < text.length) segs.push({ kind: 'text', content: text.slice(cursor) });
  return segs;
}

function AnnotatedText({
  text,
  issues,
  visibleSet,
  activeIndex,
  onIssueClick,
}: {
  text: string;
  issues: GrammarIssue[];
  visibleSet: Set<number>;
  activeIndex: number | null;
  onIssueClick: (idx: number) => void;
}) {
  const segments = useMemo(
    () => buildSegments(text, issues, visibleSet),
    [text, issues, visibleSet],
  );

  return (
    <div className="font-serif text-base leading-relaxed text-ink whitespace-pre-wrap select-text">
      {segments.map((seg, i) => {
        if (seg.kind === 'text') return <span key={i}>{seg.content}</span>;
        const s = CATEGORY_STYLE[seg.category] ?? CATEGORY_STYLE.grammar;
        const isActive = activeIndex === seg.issueIndex;
        return (
          <mark
            key={i}
            role="button"
            tabIndex={0}
            onClick={() => onIssueClick(seg.issueIndex)}
            onKeyDown={(e) => e.key === 'Enter' && onIssueClick(seg.issueIndex)}
            className={`cursor-pointer underline decoration-wavy decoration-2 bg-transparent ${s.underline} ${isActive ? s.activeBg + ' rounded-sm px-0.5' : ''} transition-colors`}
          >
            {seg.content}
          </mark>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Issue card
// ---------------------------------------------------------------------------

function IssueCard({
  issue,
  index,
  active,
  onAccept,
  onIgnore,
  onClick,
  cardRef,
}: {
  issue: GrammarIssue;
  index: number;
  active: boolean;
  onAccept: (idx: number) => void;
  onIgnore: (idx: number) => void;
  onClick: (idx: number) => void;
  cardRef: (el: HTMLDivElement | null) => void;
}) {
  const s = CATEGORY_STYLE[issue.category] ?? CATEGORY_STYLE.grammar;

  return (
    <div
      ref={cardRef}
      onClick={() => onClick(index)}
      className={`rounded-xl border cursor-pointer transition-all ${
        active ? 'border-stone-400 shadow-sm ring-1 ring-stone-300' : 'border-stone-200 hover:border-stone-300'
      } bg-white overflow-hidden`}
    >
      <div className="p-4 space-y-2.5">
        <div className="flex items-start gap-2">
          <span className={`mt-1.5 shrink-0 w-2 h-2 rounded-full ${s.dot}`} />
          <p className="font-sans text-sm font-semibold text-ink leading-snug">
            {issue.short_label}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap pl-4">
          <span className={`font-sans text-xs px-2 py-0.5 rounded-full line-through ${s.badge}`}>
            {issue.original}
          </span>
          <span className="text-stone-400 text-xs">→</span>
          <span className="font-sans text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800">
            {issue.replacement}
          </span>
        </div>

        <p className="font-sans text-xs text-stone-500 leading-relaxed pl-4">
          {issue.explanation}
        </p>
      </div>

      <div className="flex gap-2 px-4 pb-3" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => onAccept(index)}
          className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold py-1.5 transition-colors"
        >
          Accept
        </button>
        <button
          onClick={() => onIgnore(index)}
          className="flex-1 rounded-lg border border-stone-200 hover:border-stone-300 text-stone-600 text-xs font-semibold py-1.5 transition-colors"
        >
          Ignore
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Score rings
// ---------------------------------------------------------------------------

function ScoreRing({ value, label }: { value: number; label: string }) {
  const r = 14;
  const circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ;
  const color = value >= 85 ? '#16a34a' : value >= 50 ? '#d97706' : '#dc2626';

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-9 h-9">
        <svg width="36" height="36" viewBox="0 0 36 36" className="-rotate-90">
          <circle cx="18" cy="18" r={r} fill="none" stroke="#e7e5e4" strokeWidth="3" />
          <circle
            cx="18" cy="18" r={r}
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
          />
        </svg>
        <span
          className="absolute inset-0 flex items-center justify-center font-mono text-[0.55rem] font-semibold"
          style={{ color }}
        >
          {value}
        </span>
      </div>
      <span className="font-sans text-[0.6rem] text-stone-500 text-center leading-none capitalize">
        {label}
      </span>
    </div>
  );
}

function ScoreBar({ scores }: { scores: GrammarScores }) {
  const metrics: { label: string; value: number }[] = [
    { label: 'Grammar',     value: scores.grammar },
    { label: 'Spelling',    value: scores.spelling },
    { label: 'Punctuation', value: scores.punctuation },
    { label: 'Style',       value: scores.style },
    { label: 'Overall',     value: scores.overall },
  ];

  return (
    <div className="border-t border-stone-200 bg-stone-100/50 px-4 py-3">
      <div className="flex justify-around items-center gap-2">
        {metrics.map((m) => (
          <ScoreRing key={m.label} value={m.value} label={m.label} />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type Tab = 'all' | GrammarIssue['category'];

export default function GrammarPage() {
  const [draft, setDraft, clearDraft] = useDraftPersistence('draftwell:grammar-composer');
  const words = wordCount(draft);

  const [save, setSave] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GrammarResponse | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  // Working copies updated as the user accepts fixes
  const [workingText, setWorkingText] = useState('');
  const [workingIssues, setWorkingIssues] = useState<GrammarIssue[]>([]);

  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const [accepted, setAccepted] = useState<Set<number>>(new Set());
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('all');

  const cardRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const issues = useMemo(() => result?.issues ?? [], [result]);

  const unresolvedSet = useMemo(() => {
    const s = new Set<number>();
    issues.forEach((_, idx) => {
      if (!dismissed.has(idx) && !accepted.has(idx)) s.add(idx);
    });
    return s;
  }, [issues, dismissed, accepted]);

  const liveScores = useMemo(
    () => (result ? computeScores(workingIssues, unresolvedSet, result.word_count) : null),
    [workingIssues, unresolvedSet, result],
  );

  const tabVisibleSet = useMemo(() => {
    if (activeTab === 'all') return unresolvedSet;
    const s = new Set<number>();
    issues.forEach((issue, idx) => {
      if (unresolvedSet.has(idx) && issue.category === activeTab) s.add(idx);
    });
    return s;
  }, [issues, unresolvedSet, activeTab]);

  const typeCounts = useMemo(() => {
    const c: Record<string, number> = {};
    issues.forEach((issue, idx) => {
      if (!unresolvedSet.has(idx)) return;
      c[issue.category] = (c[issue.category] ?? 0) + 1;
    });
    return c;
  }, [issues, unresolvedSet]);

  const totalUnresolved = unresolvedSet.size;
  const issueCategories = ['grammar', 'spelling', 'punctuation', 'style'] as const;
  const availableTabs = issueCategories.filter((t) => (typeCounts[t] ?? 0) > 0);

  const sortedVisible = useMemo(() => {
    return [...tabVisibleSet].sort((a, b) => {
      return (workingIssues[a]?.start ?? 0) - (workingIssues[b]?.start ?? 0);
    });
  }, [tabVisibleSet, workingIssues]);

  useEffect(() => {
    if (activeIndex === null) return;
    cardRefs.current.get(activeIndex)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [activeIndex]);

  const handleCheck = useCallback(async () => {
    if (!draft.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setSavedId(null);
    setDismissed(new Set());
    setAccepted(new Set());
    setActiveIndex(null);
    setActiveTab('all');
    try {
      const resp = await submitGrammar({ text: draft, save });
      setResult(resp);
      setWorkingText(draft);
      setWorkingIssues(resp.issues);
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
  }, [draft, save, clearDraft]);

  // 800ms debounce auto-check while in editing mode
  useEffect(() => {
    if (result !== null || !draft.trim()) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(handleCheck, 800);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [draft, result, handleCheck]);

  function handleAccept(idx: number) {
    const issue = workingIssues[idx];
    if (!issue) return;
    const delta = issue.replacement.length - issue.original.length;
    setWorkingText((prev) =>
      prev.slice(0, issue.start) + issue.replacement + prev.slice(issue.end)
    );
    setWorkingIssues((prev) =>
      prev.map((wi, i) => {
        if (i === idx) return wi;
        if (wi.start >= issue.end) {
          return { ...wi, start: wi.start + delta, end: wi.end + delta };
        }
        return wi;
      })
    );
    setAccepted((prev) => new Set([...prev, idx]));
    if (activeIndex === idx) setActiveIndex(null);
  }

  function handleAcceptAll() {
    const sorted = [...unresolvedSet]
      .map((idx) => ({ idx, issue: workingIssues[idx] }))
      .sort((a, b) => a.issue.start - b.issue.start);

    let text = workingText;
    let delta = 0;
    for (const { issue } of sorted) {
      const s = issue.start + delta;
      const e = issue.end + delta;
      text = text.slice(0, s) + issue.replacement + text.slice(e);
      delta += issue.replacement.length - issue.original.length;
    }
    setWorkingText(text);
    setAccepted(new Set(issues.map((_, i) => i)));
    setActiveIndex(null);
  }

  function handleIgnore(idx: number) {
    setDismissed((prev) => new Set([...prev, idx]));
    if (activeIndex === idx) setActiveIndex(null);
  }

  function handleReset() {
    setResult(null);
    setDismissed(new Set());
    setAccepted(new Set());
    setActiveIndex(null);
    setActiveTab('all');
    if (workingText) setDraft(workingText);
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* ── Editor ─────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <div className="px-8 py-8 max-w-3xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="font-serif text-2xl font-semibold text-ink-strong">Grammar Checker</h1>
              <p className="font-sans text-sm text-stone-500 mt-0.5">
                Find and fix grammar, spelling, and punctuation issues.
              </p>
            </div>
            <Mono className="text-[0.625rem] text-stone-400">{words} words</Mono>
          </div>

          {!result ? (
            <Textarea
              placeholder="Paste or type your draft here…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="min-h-[380px] font-serif text-base leading-relaxed"
              aria-label="Your draft"
            />
          ) : (
            <div className="min-h-[380px] rounded-lg border border-stone-200 bg-cream/40 p-5">
              <AnnotatedText
                text={workingText}
                issues={workingIssues}
                visibleSet={unresolvedSet}
                activeIndex={activeIndex}
                onIssueClick={(idx) => setActiveIndex((prev) => (prev === idx ? null : idx))}
              />
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 mt-5">
            {!result ? (
              <>
                <label className="flex items-center gap-2 cursor-pointer" htmlFor="grammar-save-switch">
                  <Switch id="grammar-save-switch" checked={save} onCheckedChange={setSave} size="sm" />
                  <SectionLabel as="span">Save draft</SectionLabel>
                </label>
                <Button size="sm" onClick={handleCheck} disabled={loading || !draft.trim()} className="text-xs ml-auto">
                  {loading ? 'Checking…' : 'Check Grammar'}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => { setDraft(''); setResult(null); setError(null); }}
                  className="text-xs"
                >
                  Clear
                </Button>
              </>
            ) : (
              <>
                <Button variant="secondary" size="sm" onClick={handleReset} className="text-xs">
                  Check again
                </Button>
                {accepted.size > 0 && (
                  <span className="font-sans text-xs text-stone-500">
                    {accepted.size} fix{accepted.size !== 1 ? 'es' : ''} applied
                  </span>
                )}
              </>
            )}
          </div>

          {error && (
            <p className="font-sans text-sm text-red-600 mt-4">{error}</p>
          )}
        </div>
      </main>

      {/* ── Results panel ──────────────────────────────────────────────── */}
      <aside
        className="w-[38%] min-w-[340px] max-w-[480px] shrink-0 border-l border-stone-200 flex flex-col bg-cream"
        aria-label="Grammar results"
        aria-live="polite"
        aria-busy={loading}
      >
        {/* Sticky header */}
        <div className="sticky top-0 z-10 bg-cream border-b border-stone-200 shrink-0">
          <div className="px-5 py-3 flex items-center justify-between">
            <h2 className="font-sans text-sm font-semibold text-ink">Grammar Checker</h2>
            {liveScores && (
              <span className={`font-sans text-xs px-2 py-0.5 rounded-full ${
                liveScores.overall_label === 'Great'      ? 'bg-green-100 text-green-800' :
                liveScores.overall_label === 'Good'       ? 'bg-stone-100 text-stone-700' :
                liveScores.overall_label === 'Fair'       ? 'bg-amber-100 text-amber-800' :
                                                            'bg-red-100 text-red-800'
              }`}>
                {liveScores.overall_label}
              </span>
            )}
          </div>

          {result && (
            <>
              <div className="flex px-2 overflow-x-auto border-b border-stone-100">
                {(['all', ...availableTabs] as Tab[]).map((tab) => {
                  const count = tab === 'all' ? totalUnresolved : (typeCounts[tab] ?? 0);
                  return (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-3 py-2 text-xs font-sans whitespace-nowrap capitalize border-b-2 transition-colors ${
                        activeTab === tab
                          ? 'border-ink text-ink font-semibold'
                          : 'border-transparent text-stone-400 hover:text-stone-600'
                      }`}
                    >
                      {tab === 'all' ? 'All' : tab}
                      {count > 0 && (
                        <span className="ml-1 text-[0.6rem] font-mono bg-stone-100 text-stone-500 rounded-full px-1.5 py-0.5">
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {totalUnresolved > 0 && (
                <div className="flex items-center justify-between px-5 py-2 bg-stone-100/50">
                  <span className="font-sans text-xs text-stone-500">
                    {totalUnresolved} suggestion{totalUnresolved !== 1 ? 's' : ''}
                  </span>
                  <button
                    onClick={handleAcceptAll}
                    className="font-sans text-xs font-semibold text-emerald-700 hover:text-emerald-800 transition-colors"
                  >
                    Accept all
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Scrollable card list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <p className="font-sans text-xs text-stone-400 text-center py-10">Checking grammar…</p>
          )}

          {result && totalUnresolved === 0 && (
            <div className="rounded-xl border border-green-200 bg-green-50 px-5 py-8 text-center mt-4">
              <p className="font-sans text-sm font-semibold text-green-800 mb-1">
                {issues.length === 0 ? 'No issues found!' : 'All issues resolved!'}
              </p>
              <p className="font-sans text-xs text-green-700">
                {issues.length === 0 ? 'Your writing looks great.' : `${accepted.size} fix${accepted.size !== 1 ? 'es' : ''} applied.`}
              </p>
            </div>
          )}

          {sortedVisible.map((idx) => (
            <IssueCard
              key={idx}
              issue={workingIssues[idx]}
              index={idx}
              active={activeIndex === idx}
              onAccept={handleAccept}
              onIgnore={handleIgnore}
              onClick={(i) => setActiveIndex((prev) => (prev === i ? null : i))}
              cardRef={(el) => {
                if (el) cardRefs.current.set(idx, el);
                else cardRefs.current.delete(idx);
              }}
            />
          ))}

          {!loading && !result && (
            <p className="font-sans text-sm text-stone-400 leading-relaxed py-4 text-center">
              Results will appear here after you check your draft.
            </p>
          )}

          {savedId && (
            <Mono className="block text-xs pt-2 text-center">
              Saved ·{' '}
              <Link href={`/documents/${savedId}`} className="underline hover:decoration-gold">
                {savedId.slice(0, 8)}…
              </Link>
            </Mono>
          )}
        </div>

        {/* Score rings — live scores derived from remaining unresolved issues */}
        {liveScores && <ScoreBar scores={liveScores} />}
      </aside>
    </div>
  );
}
