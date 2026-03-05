import { Eraser, Pen, Play, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'

interface CommandBarProps {
  onTakeATurn(): void
  onContinue(): void
  onRetry(): void
  onErase(): void
  takeATurnDisabled?: boolean
  continueDisabled?: boolean
  retryDisabled?: boolean
  eraseDisabled?: boolean
  retryTitle?: string
  eraseTitle?: string
}

export function CommandBar({
  onTakeATurn,
  onContinue,
  onRetry,
  onErase,
  takeATurnDisabled = false,
  continueDisabled = false,
  retryDisabled = false,
  eraseDisabled = false,
  retryTitle,
  eraseTitle,
}: CommandBarProps) {
  return (
    <nav className="surface-card command-bar flex gap-2 overflow-x-auto rounded-full p-2" role="toolbar" aria-label="叙事控制">
      <Button className="min-w-max" onClick={onTakeATurn} disabled={takeATurnDisabled} title="输入你的行动，改变故事走向">
        <Pen className="mr-1.5 size-3.5" />
        我来互动
      </Button>
      <Button variant="primary" className="min-w-max" onClick={onContinue} disabled={continueDisabled} title="让故事继续推进">
        <Play className="mr-1.5 size-3.5" />
        继续体验
      </Button>
      <Button variant="ghost" className="min-w-max" onClick={onRetry} disabled={retryDisabled} title={retryTitle ?? '重新生成上一段叙事'}>
        <RefreshCw className="mr-1.5 size-3.5" />
        重新生成
      </Button>
      <Button variant="ghost" className="min-w-max" onClick={onErase} disabled={eraseDisabled} title={eraseTitle ?? '删除上一段叙事'}>
        <Eraser className="mr-1.5 size-3.5" />
        擦除
      </Button>
    </nav>
  )
}
