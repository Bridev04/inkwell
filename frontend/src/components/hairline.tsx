import { cn } from '@/lib/utils';

interface HairlineProps extends React.HTMLAttributes<HTMLHRElement> {
  variant?: 'default' | 'gold';
}

export function Hairline({ variant = 'default', className, ...props }: HairlineProps) {
  return (
    <hr
      className={cn(
        'border-0 border-t',
        variant === 'default' ? 'border-stone-300 w-full' : 'border-gold w-12',
        className
      )}
      {...props}
    />
  );
}
