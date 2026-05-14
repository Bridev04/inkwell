'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  submitFeedback,
  streamRewrite,
  type FeedbackResponse,
  type RewriteStyle,
  type RewriteDoneEvent,
  type RewriteErrorEvent,
  type RewriteDocumentEvent,
} from '@/lib/api';
import { addSavedDoc } from '@/lib/savedDocs';

export default function Home() {
  const [draft, setDraft] = useState('');
  const [style, setStyle] = useState<RewriteStyle>('formal');
  const [save, setSave] = useState(false);

  const [feedbackResult, setFeedbackResult] = useState<FeedbackResponse | null>(null);
  const [rewriteText, setRewriteText] = useState('');
  const [rewriteMeta, setRewriteMeta] = useState<
    (RewriteDoneEvent | RewriteErrorEvent | RewriteDocumentEvent)[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFeedback() {
    setLoading(true);
    setError(null);
    setFeedbackResult(null);
    try {
      const resp = await submitFeedback({ text: draft, save });
      setFeedbackResult(resp);
      if (save && resp.document_id) {
        addSavedDoc({
          id: resp.document_id,
          createdAt: new Date().toISOString(),
          snippet: draft.slice(0, 80),
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  async function handleRewrite() {
    setLoading(true);
    setError(null);
    setRewriteText('');
    setRewriteMeta([]);
    try {
      await streamRewrite(
        { text: draft, style, save },
        {
          onToken: (evt) => setRewriteText((t) => t + evt.text),
          onDone: (evt) => setRewriteMeta((m) => [...m, evt]),
          onError: (evt) => setRewriteMeta((m) => [...m, evt]),
          onDocument: (evt) => {
            setRewriteMeta((m) => [...m, evt]);
            if (save) {
              addSavedDoc({
                id: evt.document_id,
                createdAt: new Date().toISOString(),
                snippet: draft.slice(0, 80),
              });
            }
          },
        }
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Draftwell</h1>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Draft</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Textarea
            placeholder="Paste your draft here..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="min-h-40"
          />
          <div className="flex items-center gap-4">
            <label htmlFor="style">Rewrite style:</label>
            <select
              id="style"
              value={style}
              onChange={(e) => setStyle(e.target.value as RewriteStyle)}
              className="border rounded px-2 py-1"
            >
              <option value="formal">Formal</option>
              <option value="casual">Casual</option>
              <option value="persuasive">Persuasive</option>
              <option value="concise">Concise</option>
              <option value="vivid">Vivid</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="save-switch"
              checked={save}
              onCheckedChange={(checked) => setSave(checked)}
            />
            <label htmlFor="save-switch">Save draft</label>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleFeedback} disabled={loading || !draft}>
              Get Feedback
            </Button>
            <Button
              onClick={handleRewrite}
              disabled={loading || !draft}
              variant="outline"
            >
              Get Rewrite
            </Button>
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
        </CardContent>
      </Card>

      {feedbackResult && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Feedback Response</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs overflow-auto whitespace-pre-wrap">
              {JSON.stringify(feedbackResult, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {(rewriteText || rewriteMeta.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>Rewrite Stream</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {rewriteText && <p className="whitespace-pre-wrap">{rewriteText}</p>}
            {rewriteMeta.length > 0 && (
              <pre className="text-xs overflow-auto whitespace-pre-wrap">
                {JSON.stringify(rewriteMeta, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      )}
    </main>
  );
}
