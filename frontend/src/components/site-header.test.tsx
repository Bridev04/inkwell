import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SiteHeader } from './site-header';

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
}));

vi.mock('next/image', () => ({
  default: ({ alt, ...props }: { alt: string; [key: string]: unknown }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={alt} {...props} />
  ),
}));

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe('SiteHeader', () => {
  it('renders a link to / wrapping the wordmark', () => {
    render(<SiteHeader />);
    const homeLink = screen.getByRole('link', { name: /draftwell home/i });
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('renders a "Saved drafts" navigation link', () => {
    render(<SiteHeader />);
    expect(screen.getByRole('link', { name: /saved drafts/i })).toBeInTheDocument();
  });

  it('applies active styling when the current path is /documents', async () => {
    const { usePathname } = await import('next/navigation');
    vi.mocked(usePathname).mockReturnValue('/documents');

    render(<SiteHeader />);
    const link = screen.getByRole('link', { name: /saved drafts/i });
    expect(link.className).toContain('border-gold');
  });

  it('does not apply active styling when the current path is /', async () => {
    const { usePathname } = await import('next/navigation');
    vi.mocked(usePathname).mockReturnValue('/');

    render(<SiteHeader />);
    const link = screen.getByRole('link', { name: /saved drafts/i });
    expect(link.className).not.toContain('border-gold');
  });
});
