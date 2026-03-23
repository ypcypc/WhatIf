/**
 * React hook wrapping the Web Speech API.
 * Two modes:
 *   - push-to-talk (continuous=false): single utterance per startListening()
 *   - conversation  (continuous=true):  keeps listening, auto-submits after silence
 */

import { useState, useRef, useCallback, useEffect } from 'react'

interface SpeechRecognitionResult {
  transcript: string
  isListening: boolean
  startListening: (opts?: { continuous?: boolean }) => void
  stopListening: () => void
  supported: boolean
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
  resultIndex: number
}

type WebkitSpeechRecognition = new () => {
  lang: string
  continuous: boolean
  interimResults: boolean
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: Event & { error: string }) => void) | null
  onend: (() => void) | null
}

interface SpeechRecognitionInstance {
  lang: string
  continuous: boolean
  interimResults: boolean
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: Event & { error: string }) => void) | null
  onend: (() => void) | null
}

function getRecognitionClass(): WebkitSpeechRecognition | null {
  const speechWindow = window as Window & typeof globalThis & {
    SpeechRecognition?: WebkitSpeechRecognition
    webkitSpeechRecognition?: WebkitSpeechRecognition
  }
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null
}

const SILENCE_SHORT = 2500  // ms silence before auto-submit (short text)
const SILENCE_LONG = 3000   // ms silence for longer text (>20 chars)

export function useSpeechRecognition(
  lang = 'zh-CN',
  onSilenceSubmit?: (text: string) => void,
): SpeechRecognitionResult {
  const [transcript, setTranscript] = useState('')
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const continuousModeRef = useRef(false)
  const transcriptRef = useRef('')
  const onSilenceSubmitRef = useRef(onSilenceSubmit)
  const sessionIdRef = useRef(0)
  const supported = !!getRecognitionClass()

  useEffect(() => {
    onSilenceSubmitRef.current = onSilenceSubmit
  }, [onSilenceSubmit])

  function clearSilenceTimer() {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      sessionIdRef.current += 1
      continuousModeRef.current = false
      const recognition = recognitionRef.current
      recognitionRef.current = null
      recognition?.abort()
      clearSilenceTimer()
    }
  }, [])

  const startListening = useCallback((opts?: { continuous?: boolean }) => {
    const SpeechRecognition = getRecognitionClass()
    if (!SpeechRecognition) return

    sessionIdRef.current += 1
    const sessionId = sessionIdRef.current
    const previousRecognition = recognitionRef.current
    recognitionRef.current = null
    previousRecognition?.abort()
    clearSilenceTimer()

    const continuous = opts?.continuous ?? false
    continuousModeRef.current = continuous

    const recognition = new SpeechRecognition()
    recognition.lang = lang
    recognition.continuous = continuous
    recognition.interimResults = true
    recognitionRef.current = recognition

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (sessionIdRef.current !== sessionId || recognitionRef.current !== recognition) return

      let finalTranscript = ''
      let interimTranscript = ''

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        } else {
          interimTranscript += result[0].transcript
        }
      }

      const current = finalTranscript || interimTranscript
      transcriptRef.current = current
      setTranscript(current)

      if (continuous && current.trim()) {
        clearSilenceTimer()
        const delay = current.length > 20 ? SILENCE_LONG : SILENCE_SHORT
        silenceTimerRef.current = setTimeout(() => {
          if (sessionIdRef.current !== sessionId || recognitionRef.current !== recognition) return

          const text = transcriptRef.current.trim()
          if (text && onSilenceSubmitRef.current) {
            continuousModeRef.current = false
            recognitionRef.current = null
            recognition.onend = null
            try { recognition.stop() } catch { /* already stopped */ }
            clearSilenceTimer()
            setIsListening(false)
            transcriptRef.current = ''
            setTranscript('')
            onSilenceSubmitRef.current(text)
          }
        }, delay)
      }
    }

    recognition.onerror = (e) => {
      if (sessionIdRef.current !== sessionId || recognitionRef.current !== recognition) return

      if (continuous && e.error === 'no-speech') return
      setIsListening(false)
      clearSilenceTimer()
    }

    recognition.onend = () => {
      if (sessionIdRef.current !== sessionId) return

      if (continuous && continuousModeRef.current && recognitionRef.current === recognition) {
        try { recognition.start() } catch { setIsListening(false) }
      } else if (recognitionRef.current === recognition) {
        recognitionRef.current = null
        setIsListening(false)
        clearSilenceTimer()
      }
    }

    setTranscript('')
    transcriptRef.current = ''
    setIsListening(true)
    recognition.start()
  }, [lang])

  const stopListening = useCallback(() => {
    sessionIdRef.current += 1
    continuousModeRef.current = false
    const recognition = recognitionRef.current
    recognitionRef.current = null
    if (recognition) {
      recognition.onend = null
      try { recognition.stop() } catch { /* already stopped */ }
    }
    transcriptRef.current = ''
    setTranscript('')
    setIsListening(false)
    clearSilenceTimer()
  }, [])

  return { transcript, isListening, startListening, stopListening, supported }
}
