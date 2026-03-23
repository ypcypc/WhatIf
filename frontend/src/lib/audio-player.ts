/**
 * AudioPlayer — decodes base64 MP3 audio and plays segments sequentially.
 * Singleton pattern; call unlock() on a user gesture before first playback.
 */

class AudioPlayer {
  private ctx: AudioContext | null = null
  private queue: AudioBuffer[] = []
  private currentSource: AudioBufferSourceNode | null = null
  private playing = false
  private stopped = false

  /** Playback speed multiplier (1 = normal, 10 = 10x speed). */
  playbackRate = 1

  /** Called when all queued audio finishes playing (queue drained). */
  onComplete: (() => void) | null = null

  /** Create / resume AudioContext. Must be called from a user gesture. */
  unlock(): void {
    if (!this.ctx) {
      this.ctx = new AudioContext()
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume()
    }
  }

  /** Enqueue base64-encoded MP3 audio for sequential playback. */
  async enqueue(mp3Base64: string): Promise<void> {
    if (this.stopped) return
    if (!this.ctx) this.unlock()

    const binary = atob(mp3Base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }

    try {
      const buffer = await this.ctx!.decodeAudioData(bytes.buffer.slice(0))
      if (this.stopped) return
      this.queue.push(buffer)
      if (!this.playing) this.playNext()
    } catch { /* decode failed */ }
  }

  /** Stop all audio and clear the queue. */
  stop(): void {
    this.stopped = true
    this.queue.length = 0
    if (this.currentSource) {
      try {
        this.currentSource.onended = null
        this.currentSource.stop()
      } catch { /* already stopped */ }
      this.currentSource = null
    }
    this.playing = false
  }

  /** Reset stopped flag to allow new playback (call before new stream). */
  reset(): void {
    this.stopped = false
  }

  get isPlaying(): boolean {
    return this.playing
  }

  private playNext(): void {
    if (this.stopped || this.queue.length === 0) {
      const wasPlaying = this.playing
      this.playing = false
      if (wasPlaying && !this.stopped && this.onComplete) {
        this.onComplete()
      }
      return
    }

    this.playing = true
    const buffer = this.queue.shift()!
    const source = this.ctx!.createBufferSource()
    source.buffer = buffer
    source.playbackRate.value = this.playbackRate
    source.connect(this.ctx!.destination)
    source.onended = () => {
      this.currentSource = null
      this.playNext()
    }
    this.currentSource = source
    source.start()
  }
}

export const audioPlayer = new AudioPlayer()
