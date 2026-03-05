import type { KeyboardEvent, RefObject } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

interface ActionComposerProps {
  value: string
  onChange(text: string): void
  onCancel(): void
  onSubmit(): void
  onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void
  textareaRef: RefObject<HTMLTextAreaElement | null>
}

export function ActionComposer({
  value,
  onChange,
  onCancel,
  onSubmit,
  onKeyDown,
  textareaRef,
}: ActionComposerProps) {
  return (
    <section className="surface-card composer-shell fixed right-4 bottom-4 left-4 z-10 mx-auto w-auto max-w-[960px] rounded-2xl p-3">
      <div className="space-y-3">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="你想做什么？"
        />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            取消
          </Button>
          <Button onClick={onSubmit}>执行</Button>
        </div>
      </div>
    </section>
  )
}
