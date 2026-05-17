import { cn } from '@/lib/utils';

interface SkipLinkProps {
  href: string;
  label: string;
  className?: string;
}

export function SkipLink({ href, label, className }: SkipLinkProps) {
  return (
    <a
      href={href}
      className={cn(
        'sr-only',
        'focus-visible:not-sr-only focus-visible:fixed focus-visible:top-4 focus-visible:left-4 focus-visible:z-50',
        'focus-visible:bg-cream focus-visible:border focus-visible:border-gold focus-visible:rounded-md',
        'focus-visible:px-4 focus-visible:py-2 focus-visible:font-sans focus-visible:text-sm focus-visible:text-ink',
        className
      )}
    >
      {label}
    </a>
  );
}
