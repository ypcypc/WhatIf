import { Menu, Sparkles, Undo2, Redo2, Settings } from 'lucide-react'

import { Button } from '@/components/ui/button'

interface TopBarProps {
  title: string
  onGameMenu(): void
  onModelSwitcher(): void
  onUndo(): void
  onRedo(): void
  onSettings(): void
}

export function TopBar({
  title,
  onGameMenu,
  onModelSwitcher,
  onUndo,
  onRedo,
  onSettings,
}: TopBarProps) {
  return (
    <header className="surface-card flex items-center gap-2 rounded-2xl p-2">
      <Button size="icon" onClick={onGameMenu} aria-label="Game Menu">
        <Menu className="size-4" />
      </Button>
      <div className="min-w-0 flex-1 px-2">
        <p className="truncate text-sm font-semibold tracking-wide text-[var(--text-primary)]">{title}</p>
      </div>
      <Button size="icon" onClick={onModelSwitcher} aria-label="Model Switcher">
        <Sparkles className="size-4" />
      </Button>
      <Button size="icon" onClick={onUndo} aria-label="Undo">
        <Undo2 className="size-4" />
      </Button>
      <Button size="icon" onClick={onRedo} aria-label="Redo">
        <Redo2 className="size-4" />
      </Button>
      <Button size="icon" onClick={onSettings} aria-label="Settings">
        <Settings className="size-4" />
      </Button>
    </header>
  )
}
