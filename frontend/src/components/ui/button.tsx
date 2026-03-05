import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/cn'

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-semibold cursor-pointer transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-[var(--action-accent)] focus-visible:ring-offset-0',
  {
    variants: {
      variant: {
        default:
          'border border-[var(--border)] bg-[rgba(18,14,8,0.72)] text-[var(--text-primary)] shadow-[0_8px_20px_rgba(0,0,0,0.28)] hover:bg-[rgba(18,14,8,0.92)] hover:border-[var(--border-hover)] active:scale-[0.98]',
        primary:
          'border border-[rgba(196,163,90,0.4)] bg-[rgba(196,163,90,0.12)] text-[var(--action-accent)] shadow-[0_0_12px_rgba(196,163,90,0.12)] hover:bg-[rgba(196,163,90,0.2)] hover:shadow-[0_0_16px_rgba(196,163,90,0.22)] active:scale-[0.98]',
        ghost:
          'border border-[rgba(196,163,90,0.12)] bg-[rgba(18,14,8,0.42)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border)] active:scale-[0.98]',
      },
      size: {
        default: 'h-10 px-4',
        sm: 'h-8 rounded-lg px-3 text-xs',
        lg: 'h-11 rounded-xl px-6',
        icon: 'size-11',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

type ButtonProps = React.ComponentProps<'button'> & VariantProps<typeof buttonVariants>

function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size, className }))} {...props} />
}

export { Button }
