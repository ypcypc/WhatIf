import * as React from 'react'

import { cn } from '@/lib/cn'

const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<'textarea'>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'flex min-h-28 w-full rounded-2xl border border-[var(--border)] bg-[rgba(14,11,6,0.72)] px-4 py-3 text-sm text-[var(--text-primary)] shadow-[inset_0_1px_0_rgba(196,163,90,0.06)] outline-none placeholder:text-[var(--text-secondary)] focus-visible:ring-2 focus-visible:ring-[var(--action-accent)]',
        className,
      )}
      {...props}
    />
  ),
)
Textarea.displayName = 'Textarea'

export { Textarea }
