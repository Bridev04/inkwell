'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, PenLine, FolderOpen, Settings } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { href: '/desk', label: 'Writing Desk', icon: PenLine, exact: false },
  { href: '/documents', label: 'Documents', icon: FolderOpen, exact: false },
  { href: '/settings', label: 'Settings', icon: Settings, exact: true },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 min-h-screen bg-cream border-r border-stone-300 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-stone-300">
        <Link href="/" aria-label="Draftwell home">
          <Image
            src="/brand/wordmark.png"
            alt="Draftwell"
            width={461}
            height={113}
            className="h-6 w-auto"
          />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5" aria-label="Main navigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon, exact }) => {
          const isActive = exact
            ? pathname === href
            : pathname === href || pathname.startsWith(href + '/');

          return (
            <Link
              key={href}
              href={href}
              className={[
                'flex items-center gap-3 px-3 py-2 rounded-md font-sans text-sm transition-colors duration-150',
                isActive
                  ? 'bg-stone-300/50 text-ink-strong font-medium'
                  : 'text-stone-500 hover:text-ink hover:bg-stone-300/30',
              ].join(' ')}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon size={15} aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Brand tagline */}
      <div className="px-5 py-4 border-t border-stone-300">
        <p className="font-mono text-[0.625rem] text-stone-500 uppercase tracking-widest">
          AI · Refine · Create
        </p>
      </div>
    </aside>
  );
}
