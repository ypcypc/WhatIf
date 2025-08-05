import { type FC, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../utils/cn'

interface SimpleGlassProps {
  children: ReactNode
  className?: string
  blur?: 'sm' | 'md' | 'lg' | 'xl'
  opacity?: 'low' | 'medium' | 'high'
  border?: boolean
  shadow?: boolean
  animate?: boolean
  onClick?: () => void
  style?: React.CSSProperties
}

// Glass effect variants
const blurClasses = {
  sm: 'backdrop-blur-sm',
  md: 'backdrop-blur-md', 
  lg: 'backdrop-blur-lg',
  xl: 'backdrop-blur-xl'
}

const opacityClasses = {
  low: 'bg-white/5 border-white/10',
  medium: 'bg-white/10 border-white/20',
  high: 'bg-white/20 border-white/30'
}

export const SimpleGlass: FC<SimpleGlassProps> = ({
  children,
  className,
  blur = 'lg',
  opacity = 'medium',
  border = true,
  shadow = true,
  animate = true,
  onClick,
  style
}) => {
  const Component = animate ? motion.div : 'div'
  
  const animationProps = animate ? {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { type: 'spring' as const, stiffness: 300, damping: 30 }
  } : {}

  return (
    <Component
      className={cn(
        'relative rounded-2xl',
        blurClasses[blur],
        opacityClasses[opacity],
        border && 'border',
        shadow && 'shadow-xl shadow-black/25',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
      style={style}
      {...animationProps}
    >
      {children}
    </Component>
  )
}