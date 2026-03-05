import type { GameState, SSEStatePayload } from '@/types/gameplay'

export async function startGame(
  onChunk: (text: string) => void,
  onComplete: () => void,
  onState?: (state: SSEStatePayload) => void,
): Promise<void> {
  const res = await fetch('/api/game/start', { method: 'POST' })
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  if (!res.body) throw new Error('响应流为空')
  await readSSEStream(res.body, onChunk, onComplete, onState)
}

export async function getGameState(): Promise<GameState> {
  const res = await fetch('/api/game/state')
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  return res.json()
}

// ===== SSE 流式 =====

async function readSSEStream(
  body: ReadableStream<Uint8Array>,
  onChunk: (text: string) => void,
  onComplete: () => void,
  onState?: (state: SSEStatePayload) => void,
): Promise<void> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // 按 SSE 消息分割（双换行）
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const lines = part.split('\n')
      let eventType = ''
      let data = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) eventType = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }

      if (eventType === 'chunk' && data) {
        onChunk(JSON.parse(data).text)
      } else if (eventType === 'state' && data) {
        onState?.(JSON.parse(data) as SSEStatePayload)
      } else if (eventType === 'error' && data) {
        throw new Error(JSON.parse(data).message || '生成失败')
      } else if (eventType === 'done') {
        onComplete()
        return
      }
    }
  }

  onComplete()
}

export async function continueGame(
  onChunk: (text: string) => void,
  onComplete: () => void,
  onState?: (state: SSEStatePayload) => void,
): Promise<void> {
  const res = await fetch('/api/game/continue', { method: 'POST' })
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  if (!res.body) throw new Error('响应流为空')
  await readSSEStream(res.body, onChunk, onComplete, onState)
}

export async function submitAction(
  action: string,
  onChunk: (text: string) => void,
  onComplete: () => void,
  onState?: (state: SSEStatePayload) => void,
): Promise<void> {
  const res = await fetch('/api/game/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  })
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  if (!res.body) throw new Error('响应流为空')
  await readSSEStream(res.body, onChunk, onComplete, onState)
}
