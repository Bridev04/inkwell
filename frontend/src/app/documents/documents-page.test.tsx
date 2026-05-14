import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import DocumentsPage from './page';
import type { SavedDocRef } from '@/lib/savedDocs';

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/documents'),
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

vi.mock('@/lib/savedDocs', () => ({
  useSavedDocs: vi.fn(() => [] as SavedDocRef[]),
}));

vi.mock('@/components/hairline', () => ({
  Hairline: () => <hr />,
}));

describe('DocumentsPage', () => {
  it('shows the empty state when there are no saved docs', () => {
    render(<DocumentsPage />);
    expect(
      screen.getByText(/no saved drafts yet/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /write a draft/i })
    ).toBeInTheDocument();
  });

  it('renders a list of cards when saved docs exist', async () => {
    const { useSavedDocs } = await import('@/lib/savedDocs');
    vi.mocked(useSavedDocs).mockReturnValue([
      {
        id: 'doc-abc',
        createdAt: new Date(2026, 4, 14, 10, 30).toISOString(),
        snippet: 'The quick brown fox',
      },
      {
        id: 'doc-def',
        createdAt: new Date(2026, 4, 15, 9, 0).toISOString(),
        snippet: 'Another draft here',
      },
    ]);

    render(<DocumentsPage />);

    expect(screen.getAllByText(/open →/i)).toHaveLength(2);
    expect(screen.getByText('The quick brown fox')).toBeInTheDocument();
    expect(screen.getByText('Another draft here')).toBeInTheDocument();
  });

  it('card links route to the correct document URL', async () => {
    const { useSavedDocs } = await import('@/lib/savedDocs');
    vi.mocked(useSavedDocs).mockReturnValue([
      {
        id: 'doc-xyz',
        createdAt: new Date().toISOString(),
        snippet: 'Sample',
      },
    ]);

    render(<DocumentsPage />);

    // The card wrapper is an <a> linking to the document
    const cardLinks = screen.getAllByRole('link').filter(
      (el) => (el as HTMLAnchorElement).href?.includes('/documents/doc-xyz')
    );
    expect(cardLinks.length).toBeGreaterThanOrEqual(1);
  });

  it('card links are keyboard-focusable', async () => {
    const { useSavedDocs } = await import('@/lib/savedDocs');
    vi.mocked(useSavedDocs).mockReturnValue([
      {
        id: 'doc-focus',
        createdAt: new Date().toISOString(),
        snippet: 'Focusable card test',
      },
    ]);

    render(<DocumentsPage />);

    const cardLinks = screen.getAllByRole('link').filter(
      (el) => (el as HTMLAnchorElement).href?.includes('/documents/doc-focus')
    );
    expect(cardLinks[0]).not.toHaveAttribute('tabindex', '-1');
  });
});
