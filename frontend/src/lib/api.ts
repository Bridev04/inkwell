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

export interface DocumentRead {
  id: string;
  original_text: string;
  created_at: string;
  feedbacks: FeedbackRead[];
  rewrites: RewriteRead[];
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function baseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
}

async function throwIfNotOk(res: Response): Promise<void> {
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} ${res.statusText}: ${body}`);
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

export async function getDocument(id: string): Promise<DocumentRead> {
  const res = await fetch(`${baseUrl()}/api/v1/documents/${id}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  await throwIfNotOk(res);
  return res.json() as Promise<DocumentRead>;
}
