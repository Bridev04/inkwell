import { parseSSE } from './sse';

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

// ---------------------------------------------------------------------------
// Feedback types (mirrors backend/app/schemas/feedback.py)
// ---------------------------------------------------------------------------

export type FocusDimension = 'clarity' | 'tone' | 'structure';

export interface DimensionFeedback {
  name: FocusDimension;
  score: number;
  observations: string[];
  suggestions: string[];
}

export interface FeedbackRequest {
  text: string;
  focus?: FocusDimension[];
  audience?: string;
  save?: boolean;
}

export interface FeedbackResponse {
  request_id: string;
  overall_summary: string;
  dimensions: DimensionFeedback[];
  suggested_rewrites: string[];
  model_used: string;
  tokens_used: TokenUsage;
  document_id: string | null;
}

// ---------------------------------------------------------------------------
// Rewrite types (mirrors backend/app/schemas/rewrite.py)
// ---------------------------------------------------------------------------

export type RewriteStyle = 'formal' | 'casual' | 'persuasive' | 'concise' | 'vivid';

export interface RewriteRequest {
  text: string;
  style: RewriteStyle;
  audience?: string;
  save?: boolean;
}

export interface RewriteTokenEvent {
  text: string;
}

export interface RewriteDoneEvent {
  request_id: string;
  model_used: string;
  tokens_used: TokenUsage;
  latency_ms: number;
}

export interface RewriteErrorEvent {
  request_id: string;
  message: string;
}

export interface RewriteDocumentEvent {
  document_id: string;
}

// ---------------------------------------------------------------------------
// Grammar types (mirrors backend/app/schemas/grammar.py)
// ---------------------------------------------------------------------------

export type GrammarIssueCategory = 'grammar' | 'spelling' | 'punctuation' | 'style';

export interface GrammarIssue {
  id: string;
  category: GrammarIssueCategory;
  start: number;
  end: number;
  original: string;
  replacement: string;
  short_label: string;
  explanation: string;
}

export interface GrammarScores {
  grammar: number;
  spelling: number;
  punctuation: number;
  style: number;
  overall: number;
  overall_label: 'Needs work' | 'Fair' | 'Good' | 'Great';
}

export interface GrammarRequest {
  text: string;
  save?: boolean;
}

export interface GrammarResponse {
  document_id: string | null;
  corrected_text: string;
  issues: GrammarIssue[];
  scores: GrammarScores;
  word_count: number;
}

// ---------------------------------------------------------------------------
// Paraphrase types (mirrors backend/app/schemas/paraphrase.py)
// ---------------------------------------------------------------------------

export type ParaphraseMode = 'standard' | 'simpler' | 'shorter' | 'academic' | 'creative';

export interface ParaphraseRequest {
  text: string;
  mode?: ParaphraseMode;
  save?: boolean;
}

export interface ParaphraseTokenEvent {
  text: string;
}

export interface ParaphraseDoneEvent {
  request_id: string;
  model_used: string;
  tokens_used: TokenUsage;
  latency_ms: number;
}

export interface ParaphraseErrorEvent {
  request_id: string;
  message: string;
}

export interface ParaphraseDocumentEvent {
  document_id: string;
}

// ---------------------------------------------------------------------------
// Document types (mirrors backend/app/schemas/documents.py)
// ---------------------------------------------------------------------------

export interface FeedbackRead {
  id: string;
  result: Record<string, unknown>;
  created_at: string;
}

export interface RewriteRead {
  id: string;
  style: string;
  output: string;
  created_at: string;
}

export interface GrammarCheckRead {
  id: string;
  result: Record<string, unknown>;
  corrected_text: string;
  created_at: string;
}

export interface ParaphraseRead {
  id: string;
  mode: string;
  output: string;
  created_at: string;
}

export interface DocumentRead {
  id: string;
  original_text: string;
  created_at: string;
  feedbacks: FeedbackRead[];
  rewrites: RewriteRead[];
  grammar_checks: GrammarCheckRead[];
  paraphrases: ParaphraseRead[];
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function baseUrl(): string {
  // In the browser, all /api/* requests are proxied by Next.js to the backend,
  // so relative paths work regardless of environment.
  // In server contexts (if ever called SSR), fall back to the full URL.
  if (typeof window !== 'undefined') return '';
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
}

async function throwIfNotOk(res: Response): Promise<void> {
  if (!res.ok) {
    let detail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const json = await res.json();
      if (typeof json?.detail === 'string') detail = json.detail;
    } catch {
      // non-JSON body — use the status line only, never surface raw HTML/stack traces
    }
    throw new Error(detail);
  }
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function submitFeedback(
  req: FeedbackRequest
): Promise<FeedbackResponse> {
  const res = await fetch(`${baseUrl()}/api/v1/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(req),
  });
  await throwIfNotOk(res);
  return res.json() as Promise<FeedbackResponse>;
}

export async function streamRewrite(
  req: RewriteRequest,
  handlers: {
    onToken: (evt: RewriteTokenEvent) => void;
    onDone: (evt: RewriteDoneEvent) => void;
    onError: (evt: RewriteErrorEvent) => void;
    onDocument: (evt: RewriteDocumentEvent) => void;
  }
): Promise<void> {
  const res = await fetch(`${baseUrl()}/api/v1/rewrites`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(req),
  });
  await throwIfNotOk(res);
  await parseSSE(res, {
    token: (data) => handlers.onToken(data as RewriteTokenEvent),
    done: (data) => handlers.onDone(data as RewriteDoneEvent),
    error: (data) => handlers.onError(data as RewriteErrorEvent),
    document: (data) => handlers.onDocument(data as RewriteDocumentEvent),
  });
}

export async function submitGrammar(
  req: GrammarRequest
): Promise<GrammarResponse> {
  const res = await fetch(`${baseUrl()}/api/v1/grammar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(req),
  });
  await throwIfNotOk(res);
  return res.json() as Promise<GrammarResponse>;
}

export async function streamParaphrase(
  req: ParaphraseRequest,
  handlers: {
    onToken: (evt: ParaphraseTokenEvent) => void;
    onDone: (evt: ParaphraseDoneEvent) => void;
    onError: (evt: ParaphraseErrorEvent) => void;
    onDocument: (evt: ParaphraseDocumentEvent) => void;
  }
): Promise<void> {
  const res = await fetch(`${baseUrl()}/api/v1/paraphrase`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(req),
  });
  await throwIfNotOk(res);
  await parseSSE(res, {
    token: (data) => handlers.onToken(data as ParaphraseTokenEvent),
    done: (data) => handlers.onDone(data as ParaphraseDoneEvent),
    error: (data) => handlers.onError(data as ParaphraseErrorEvent),
    document: (data) => handlers.onDocument(data as ParaphraseDocumentEvent),
  });
}

export async function listDocuments(): Promise<DocumentRead[]> {
  const res = await fetch(`${baseUrl()}/api/v1/documents`, {
    credentials: 'include',
  });
  await throwIfNotOk(res);
  return res.json() as Promise<DocumentRead[]>;
}

export async function getDocument(id: string): Promise<DocumentRead> {
  const res = await fetch(`${baseUrl()}/api/v1/documents/${id}`, {
    credentials: 'include',
  });
  await throwIfNotOk(res);
  return res.json() as Promise<DocumentRead>;
}
