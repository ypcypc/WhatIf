import { type ReactNode, forwardRef, useCallback, useImperativeHandle, useRef } from 'react'

import type { StoryEntry } from '@/types/gameplay'

/** 按中文句末标点拆分为单句，每句保留标点及紧随的引号/括号 */
function splitSentences(text: string): string[] {
  const matches = text.match(/[^。！？]*[。！？][。！？"'"」』）…]*|.+$/g)
  return matches ? matches.filter((s) => s.trim()) : [text]
}

function getNearBottom(element: HTMLDivElement, threshold = 120) {
  const distance = element.scrollHeight - element.scrollTop - element.clientHeight
  return distance <= threshold
}

interface StoryViewportProps {
  storyEntries: StoryEntry[]
  showJumpToLatest: boolean
  onJumpToLatest(): void
  onNearBottomChange(isNearBottom: boolean): void
  emptySlot?: ReactNode
}

export interface StoryViewportHandle {
  scrollToBottom(behavior?: ScrollBehavior): void
  scrollToEntry(entryId: string): void
  isNearBottom(threshold?: number): boolean
}

export const StoryViewport = forwardRef<StoryViewportHandle, StoryViewportProps>(
  ({ storyEntries, showJumpToLatest, onJumpToLatest, onNearBottomChange, emptySlot }, ref) => {
    const scrollRef = useRef<HTMLDivElement>(null)

    const handleScroll = useCallback(() => {
      const element = scrollRef.current
      if (!element) return
      onNearBottomChange(getNearBottom(element))
    }, [onNearBottomChange])

    useImperativeHandle(
      ref,
      () => ({
        scrollToBottom(behavior = 'auto') {
          const element = scrollRef.current
          if (!element) return
          element.scrollTo({ top: element.scrollHeight, behavior })
        },
        scrollToEntry(entryId: string) {
          const el = scrollRef.current?.querySelector(`[data-entry-id="${entryId}"]`)
          if (el) {
            el.scrollIntoView({ block: 'start', behavior: 'smooth' })
          }
        },
        isNearBottom(threshold = 120) {
          const element = scrollRef.current
          if (!element) return true
          return getNearBottom(element, threshold)
        },
      }),
      [],
    )

    return (
      <section className="story-shell surface-card rounded-[20px]">
        <section ref={scrollRef} className="story-scroll" role="log" aria-label="故事内容" onScroll={handleScroll}>
          <div className="space-y-5">
            {storyEntries.length === 0 && emptySlot}
            {storyEntries.map((entry, index) => (
              <div key={entry.id} className="story-entry-appear">
                {index > 0 && <hr className="story-divider" />}
                <div
                  data-entry-id={entry.id}
                  className={
                    entry.kind === 'player'
                      ? 'story-copy story-copy-player'
                      : entry.status === 'error'
                        ? 'story-copy story-copy-error'
                        : 'story-copy'
                  }
                >
                  {entry.kind === 'narration'
                    ? (
                        <>
                          {entry.text
                            .split(/\n{2,}/g)
                            .filter((part) => part.trim())
                            .map((part, partIndex) => (
                              <div key={partIndex}>
                                {splitSentences(part).map((sentence, sentenceIndex) => (
                                  <p key={sentenceIndex} className="my-1">
                                    {sentence}
                                  </p>
                                ))}
                              </div>
                            ))}
                          {entry.status === 'streaming' && (
                            <p className="story-generating" aria-live="polite">
                              生成中
                              <span className="generating-dots" aria-hidden>
                                <i />
                                <i />
                                <i />
                              </span>
                            </p>
                          )}
                        </>
                      )
                    : <p>{entry.text}</p>
                  }
                </div>
              </div>
            ))}
          </div>
        </section>

        {showJumpToLatest && (
          <button className="jump-to-latest" type="button" onClick={onJumpToLatest}>
            跳到最新
          </button>
        )}
      </section>
    )
  },
)

StoryViewport.displayName = 'StoryViewport'
