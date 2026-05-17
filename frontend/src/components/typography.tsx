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
          ? 'text-[3rem] lg:text-[3.75rem]'
          : variant === 'h2'
            ? 'text-[2.25rem] lg:text-[3rem]'
            : 'text-[1.5rem] lg:text-[1.875rem]',
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
      className={cn('font-sans text-[0.9375rem] text-ink leading-[1.6] max-w-prose', className)}
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
