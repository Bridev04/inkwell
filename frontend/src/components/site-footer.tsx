import { Mono } from '@/components/typography';
import { Hairline } from '@/components/hairline';

export function SiteFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-auto">
      <Hairline />
      <div className="max-w-screen-xl mx-auto px-6 lg:px-10 py-8 flex items-center justify-between">
        <Mono>Draftwell · An AI-powered writing assistant</Mono>
        <Mono>{year}</Mono>
      </div>
    </footer>
  );
}
