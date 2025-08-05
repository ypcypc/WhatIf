import { type FC, type ReactNode } from 'react'
import { AdvancedGlass } from './AdvancedGlass'

interface GlassCardProps {
  children: ReactNode
  className?: string
  blur?: 'sm' | 'md' | 'lg' | 'xl'
  opacity?: 'low' | 'medium' | 'high'
  border?: boolean
  shadow?: boolean
  animate?: boolean
  onClick?: () => void
}


export const GlassCard: FC<GlassCardProps> = ({
  children,
  className,
  blur = 'md',
  opacity = 'medium',
  border = true,
  shadow = true,
  animate = true,
  onClick
}) => {
  return (
    <AdvancedGlass
      blur={blur}
      opacity={opacity}
      border={border}
      shadow={shadow}
      animate={animate}
      onClick={onClick}
      className={className}
      enableTilt={true}
      enableHighlight={true}
      enableDisplacement={false}
    >
      {children}
    </AdvancedGlass>
  )
}