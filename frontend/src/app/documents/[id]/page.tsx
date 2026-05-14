'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getDocument, type DocumentRead } from '@/lib/api';

export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? '';

  const [doc, setDoc] = useState<DocumentRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getDocument(id)
      .then(setDoc)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Unknown error')
      )
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <main className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Document</h1>
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-600">{error}</p>}
      {doc && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-mono truncate">{doc.id}</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs overflow-auto whitespace-pre-wrap">
              {JSON.stringify(doc, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
