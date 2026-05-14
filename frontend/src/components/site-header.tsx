'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { Hairline } from '@/components/hairline';

export function SiteHeader() {
  const pathname = usePathname();
  const isDocumentsActive =
    pathname === '/documents' || pathname.startsWith('/documents/');

  return (
    <header>
      <div className="max-w-screen-xl mx-auto px-6 lg:px-10 py-5 flex items-center justify-between">
        <Link href="/" aria-label="Draftwell home">
          <Image
            src="/brand/wordmark.png"
            alt="Draftwell"
            width={461}
            height={113}
            className="h-7 w-auto"
            preload
          />
        </Link>
        <nav aria-label="Site navigation">
          <Link
            href="/documents"
            className={
              isDocumentsActive
                ? 'font-sans text-sm text-ink-strong border-b-2 border-gold pb-0.5 transition-colors'
                : 'font-sans text-sm text-stone-500 hover:text-ink transition-colors'
            }
          >
            Saved drafts
          </Link>
        </nav>
      </div>
      <Hairline />
    </header>
  );
}
