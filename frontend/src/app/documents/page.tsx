'use client';

import Link from 'next/link';
import { SiteHeader } from '@/components/site-header';
import { SiteFooter } from '@/components/site-footer';
import { DisplayHeading, BodyProse, Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';
import { useSavedDocs } from '@/lib/savedDocs';

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

export default function DocumentsPage() {
  const docs = useSavedDocs();

  return (
    <div className="flex flex-col min-h-full">
      <SiteHeader />
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 lg:px-10 py-16">
        <DisplayHeading as="h1" variant="h2" className="mb-3">
          Saved drafts.
        </DisplayHeading>
        <BodyProse className="text-stone-500 mb-6">
          Drafts you&apos;ve saved appear below. Anonymous and stored only in this browser.
        </BodyProse>
        <Hairline className="mb-10" />

        {docs.length === 0 ? (
          <div className="text-center py-16">
            <BodyProse className="mx-auto">
              No saved drafts yet. Drafts you save on the home page will appear here.
            </BodyProse>
            <Link
              href="/"
              className="mt-4 inline-block font-sans text-sm text-ink underline decoration-stone-300 underline-offset-4 hover:decoration-gold hover:text-ink-strong transition-colors"
            >
              Write a draft →
            </Link>
          </div>
        ) : (
          <ul className="space-y-4" role="list">
            {docs.map((doc) => (
              <li key={doc.id}>
                <Link
                  href={`/documents/${doc.id}`}
                  className="group block border border-stone-300 rounded-md p-6 bg-cream hover:border-ink transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-cream"
                >
                  <DisplayHeading
                    as="h2"
                    variant="h3"
                    className="truncate mb-2"
                  >
                    {doc.snippet ? doc.snippet.slice(0, 60) : 'Untitled draft'}
                  </DisplayHeading>
                  <Mono className="block mb-3">
                    Saved{' '}
                    {dateFormatter.format(new Date(doc.createdAt))}
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
      <SiteFooter />
    </div>
  );
}
