'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { listSavedDocs, clearSavedDocs, type SavedDocRef } from '@/lib/savedDocs';

export default function DocumentsPage() {
  const [docs, setDocs] = useState<SavedDocRef[]>([]);

  useEffect(() => {
    // localStorage can only be read client-side; a post-mount effect is required
    // to avoid SSR hydration mismatch. This is the recommended external-system-sync
    // pattern, so we disable the rule that flags synchronous setState in effects.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDocs(listSavedDocs());
  }, []);

  function handleClear() {
    clearSavedDocs();
    setDocs([]);
  }

  return (
    <main className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Saved Documents</h1>
        {docs.length > 0 && (
          <Button variant="destructive" onClick={handleClear}>
            Clear all
          </Button>
        )}
      </div>

      {docs.length === 0 ? (
        <p className="text-muted-foreground">No saved drafts yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {docs.map((doc) => (
            <Card key={doc.id}>
              <CardHeader>
                <CardTitle className="text-sm font-mono truncate">{doc.id}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-1">
                <p className="text-sm text-muted-foreground">{doc.snippet}</p>
                <p className="text-xs text-muted-foreground">{doc.createdAt}</p>
                <Link
                  href={`/documents/${doc.id}`}
                  className="text-blue-600 text-sm hover:underline"
                >
                  View document →
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
