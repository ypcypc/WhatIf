import { Button } from '@/components/ui/button'

interface StartPageProps {
  onStartGame(): void
  onLoadSave(): void
}

export function StartPage({ onStartGame, onLoadSave }: StartPageProps) {
  return (
    <main className="gameplay-shell">
      <div className="background-layer background-layer-animated" />
      <div className="start-container">
        <div className="start-card surface-card rounded-[20px]">
          <h1 className="start-title">WhatIf</h1>
          <p className="start-subtitle">如果...故事可以由你改写？</p>
          <div className="start-buttons">
            <Button size="lg" variant="primary" onClick={onStartGame}>
              开始游戏
            </Button>
            <Button size="lg" variant="ghost" onClick={onLoadSave}>
              加载存档
            </Button>
          </div>
        </div>
      </div>
    </main>
  )
}
