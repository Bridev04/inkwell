import Image from 'next/image';
import Link from 'next/link';
import { SiteFooter } from '@/components/site-footer';

export default function Home() {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-cream focus:border focus:border-gold focus:rounded-md focus:px-4 focus:py-2 focus:font-sans focus:text-sm focus:text-ink"
      >
        Skip to content
      </a>

      {/* Hero */}
      <header className="min-h-[70vh] flex items-center justify-center px-6">
        <Image
          src="/brand/wordmark-vertical.png"
          alt="Draftwell — AI-powered writing assistant"
          width={686}
          height={473}
          className="w-full max-w-[360px] lg:max-w-[480px] h-auto"
          sizes="(min-width: 1024px) 480px, 360px"
          priority
        />
      </header>

      {/* CTA */}
      <main
        id="main-content"
        className="flex flex-col items-center gap-6 pb-24 px-6"
      >
        <p className="font-sans text-stone-500 text-center max-w-sm">
          AI-powered feedback, rewrites, grammar checking, and paraphrasing — all in one desk.
        </p>
        <div className="flex items-center gap-4">
          <Link
            href="/desk"
            className="inline-flex items-center gap-2 bg-ink text-cream font-sans text-sm font-medium px-6 py-2.5 rounded-md hover:bg-ink-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-cream"
          >
            Open Writing Desk →
          </Link>
          <Link
            href="/documents"
            className="font-sans text-sm text-stone-500 hover:text-ink transition-colors underline decoration-stone-300 underline-offset-4 hover:decoration-gold"
          >
            Saved drafts
          </Link>
        </div>
      </main>

      <SiteFooter />
    </>
  );
}
