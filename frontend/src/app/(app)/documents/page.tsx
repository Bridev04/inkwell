'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DisplayHeading, BodyProse, Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';
import { listDocuments, type DocumentRead } from '@/lib/api';

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function snippet(doc: DocumentRead): string {
  return doc.original_text.slice(0, 60) || 'Untitled draft';
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then(setDocs)
      .catch(() => setError('Could not load documents. Try refreshing.'));
  }, []);

  return (
    <main className="flex-1 max-w-3xl mx-auto w-full px-6 lg:px-10 py-12">
      <DisplayHeading as="h1" variant="h2" className="mb-3">
        Saved drafts.
      </DisplayHeading>
      <BodyProse className="text-stone-500 mb-6">
        Drafts you&apos;ve saved with your account appear below.
      </BodyProse>
      <Hairline className="mb-10" />

      {error && (
        <BodyProse className="text-red-600 py-6">{error}</BodyProse>
      )}

      {!error && docs === null && (
        <BodyProse className="text-stone-400 py-6">Loading…</BodyProse>
      )}

      {!error && docs !== null && docs.length === 0 && (
        <div className="text-center py-16">
          <BodyProse className="mx-auto">
            No saved drafts yet. Save a draft from the Writing Desk and it will appear here.
          </BodyProse>
          <Link
            href="/desk"
            className="mt-4 inline-block font-sans text-sm text-ink underline decoration-stone-300 underline-offset-4 hover:decoration-gold hover:text-ink-strong transition-colors"
          >
            Go to Writing Desk →
          </Link>
        </div>
      )}

      {!error && docs !== null && docs.length > 0 && (
        <ul className="space-y-4" role="list">
          {docs.map((doc) => (
            <li key={doc.id}>
              <Link
                href={`/documents/${doc.id}`}
                className="group block border border-stone-300 rounded-md p-6 bg-cream hover:border-ink transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-cream"
              >
                <DisplayHeading as="h2" variant="h3" className="truncate mb-2">
                  {snippet(doc)}
                </DisplayHeading>
                <Mono className="block mb-3">
                  Saved {dateFormatter.format(new Date(doc.created_at))}
                </Mono>
                <span className="font-sans text-sm text-ink underline decoration-stone-300 underline-offset-4 group-hover:decoration-gold group-hover:text-ink-strong transition-colors">
                  Open →
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
