import { type FC, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../utils/cn'

interface GlassButtonProps {
  children: ReactNode
  onClick?: () => void
  className?: string
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  title?: string
}

// Traditional button styles
const variantClasses = {
  primary: 'bg-white/20 hover:bg-white/30 border-white/30 text-white',
  secondary: 'bg-white/10 hover:bg-white/20 border-white/20 text-white/90',
  ghost: 'bg-transparent hover:bg-white/10 border-transparent text-white/80'
}

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg'
}

export const GlassButton: FC<GlassButtonProps> = ({
  children,
  onClick,
  className,
  variant = 'secondary',
  size = 'md',
  disabled = false,
  title
}) => {
  const handleClick = () => {
    if (!disabled && onClick) {
      onClick()
    }
  }

  // Always use traditional glass morphism
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      onClick={handleClick}
      disabled={disabled}
      title={title}
      className={cn(
        'relative rounded-lg border backdrop-blur-sm transition-all duration-200',
        'flex items-center justify-center gap-2 font-medium',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
    >
      {children}
    </motion.button>
  )
}