import { cn } from '@/lib/utils';

// `as` overrides the rendered DOM element without changing the visual scale set by `variant`.
// Use when semantic heading level must differ from visual size (e.g. h1 element that looks h2-sized).
interface DisplayHeadingProps extends React.HTMLAttributes<HTMLElement> {
  variant?: 'h1' | 'h2' | 'h3';
  as?: React.ElementType;
}

export function DisplayHeading({
  variant = 'h1',
  as: Tag,
  className,
  ...props
}: DisplayHeadingProps) {
  const Element = (Tag ?? variant) as React.ElementType;
  return (
    <Element
      className={cn(
        'font-serif text-balance tracking-tight text-ink-strong',
        variant === 'h1'
          ? 'text-5xl lg:text-6xl'
          : variant === 'h2'
            ? 'text-4xl lg:text-5xl'
            : 'text-2xl lg:text-3xl',
        className
      )}
      {...props}
    />
  );
}

interface SectionLabelProps extends React.HTMLAttributes<HTMLElement> {
  as?: 'span' | 'h2' | 'h3';
}

export function SectionLabel({
  as: Tag = 'span',
  className,
  style,
  ...props
}: SectionLabelProps) {
  return (
    <Tag
      className={cn(
        'font-sans uppercase tracking-[0.12em] text-[0.75rem] text-stone-500 [font-variant-caps:all-small-caps]',
        className
      )}
      style={style}
      {...props}
    />
  );
}

export function BodyProse({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn('font-sans text-ink leading-relaxed max-w-prose', className)}
      {...props}
    />
  );
}

export function Mono({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn('font-mono text-stone-600 text-xs', className)}
      {...props}
    />
  );
}
