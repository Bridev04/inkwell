'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { DisplayHeading, SectionLabel, BodyProse, Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';
import { getDocument, type DocumentRead } from '@/lib/api';

interface StoredFeedbackResult {
  overall_summary?: string;
  dimensions?: Array<{
    name: string;
    score: number;
    observations: string[];
    suggestions: string[];
  }>;
}

interface StoredGrammarResult {
  issues?: Array<{
    type: string;
    original: string;
    suggestion: string;
    explanation: string;
  }>;
  overall_quality?: string;
}

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'long',
  timeStyle: 'short',
});

export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? '';

  const [doc, setDoc] = useState<DocumentRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!id) return;
    getDocument(id)
      .then(setDoc)
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 lg:px-10 py-12">
        <Mono className="text-stone-500">Loading…</Mono>
      </main>
    );
  }

  if (notFound || !doc) {
    return (
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 lg:px-10 py-12">
        <DisplayHeading as="h1" variant="h2" className="mb-4">
          We couldn&apos;t find that draft.
        </DisplayHeading>
        <Link
          href="/documents"
          className="font-sans text-sm text-ink underline decoration-stone-300 underline-offset-4 hover:decoration-gold hover:text-ink-strong transition-colors"
        >
          ← Back to saved drafts
        </Link>
      </main>
    );
  }

  const title = doc.original_text.trim().slice(0, 80) || 'Untitled draft';

  return (
    <main className="flex-1 max-w-3xl mx-auto w-full px-6 lg:px-10 py-12">
      <DisplayHeading as="h1" variant="h2" className="mb-2 truncate">
        {title}
        {title.length >= 80 ? '…' : ''}
      </DisplayHeading>
      <Mono className="block mb-6">{dateFormatter.format(new Date(doc.created_at))}</Mono>
      <Hairline className="mb-10" />

      {/* Original draft */}
      {doc.original_text && (
        <section className="mb-10">
          <SectionLabel as="h2" className="mb-3 block">
            Original draft
          </SectionLabel>
          <BodyProse className="whitespace-pre-wrap">{doc.original_text}</BodyProse>
        </section>
      )}

      {/* Feedbacks */}
      {doc.feedbacks.length > 0 && (
        <section className="mb-10">
          <SectionLabel as="h2" className="mb-2 block">
            Feedback
          </SectionLabel>
          <Hairline variant="gold" className="mb-6" />
          {doc.feedbacks.map((fb) => {
            const result = fb.result as StoredFeedbackResult;
            return (
              <div key={fb.id} className="space-y-4">
                {result.overall_summary && <BodyProse>{result.overall_summary}</BodyProse>}
                {result.dimensions?.map((dim) => (
                  <div key={dim.name}>
                    <SectionLabel as="h3" className="mb-1 block capitalize">
                      {dim.name} · {dim.score}/5
                    </SectionLabel>
                    {dim.observations.map((obs, i) => (
                      <BodyProse key={i} className="text-sm">
                        {obs}
                      </BodyProse>
                    ))}
                    {dim.suggestions.length > 0 && (
                      <ul className="mt-1 pl-4 border-l-2 border-stone-300 space-y-1">
                        {dim.suggestions.map((sug, i) => (
                          <li key={i}>
                            <BodyProse className="text-sm text-stone-500">{sug}</BodyProse>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            );
          })}
        </section>
      )}

      {/* Rewrites */}
      {doc.rewrites.length > 0 && (
        <section className="mb-10">
          <SectionLabel as="h2" className="mb-2 block">
            Rewrites
          </SectionLabel>
          <Hairline variant="gold" className="mb-6" />
          <div className="space-y-8">
            {doc.rewrites.map((rw) => (
              <div key={rw.id} className="border border-stone-300 rounded-md p-6">
                <SectionLabel as="h3" className="mb-4 block capitalize">
                  {rw.style}
                </SectionLabel>
                <BodyProse className="whitespace-pre-wrap">{rw.output}</BodyProse>
                <Mono className="block mt-4">{dateFormatter.format(new Date(rw.created_at))}</Mono>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Grammar checks */}
      {doc.grammar_checks.length > 0 && (
        <section className="mb-10">
          <SectionLabel as="h2" className="mb-2 block">
            Grammar Checks
          </SectionLabel>
          <Hairline variant="gold" className="mb-6" />
          <div className="space-y-6">
            {doc.grammar_checks.map((gc) => {
              const result = gc.result as StoredGrammarResult;
              return (
                <div key={gc.id} className="border border-stone-300 rounded-md p-6 space-y-4">
                  <div className="flex items-center gap-2">
                    <SectionLabel>Quality:</SectionLabel>
                    <span className="font-sans text-sm font-medium">{result.overall_quality}</span>
                    <span className="ml-auto font-mono text-xs text-stone-500">
                      {result.issues?.length ?? 0} issue{(result.issues?.length ?? 0) !== 1 ? 's' : ''}
                    </span>
                  </div>
                  {(result.issues?.length ?? 0) > 0 && (
                    <div>
                      <SectionLabel className="block mb-2">Corrected text</SectionLabel>
                      <BodyProse className="text-sm whitespace-pre-wrap">{gc.corrected_text}</BodyProse>
                    </div>
                  )}
                  <Mono className="block">{dateFormatter.format(new Date(gc.created_at))}</Mono>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Paraphrases */}
      {doc.paraphrases.length > 0 && (
        <section className="mb-10">
          <SectionLabel as="h2" className="mb-2 block">
            Paraphrases
          </SectionLabel>
          <Hairline variant="gold" className="mb-6" />
          <div className="space-y-8">
            {doc.paraphrases.map((ph) => (
              <div key={ph.id} className="border border-stone-300 rounded-md p-6">
                <SectionLabel as="h3" className="mb-4 block capitalize">
                  {ph.mode}
                </SectionLabel>
                <BodyProse className="whitespace-pre-wrap">{ph.output}</BodyProse>
                <Mono className="block mt-4">{dateFormatter.format(new Date(ph.created_at))}</Mono>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
