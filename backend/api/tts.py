"""TTS service: sentence buffering + edge-tts synthesis."""

from __future__ import annotations

import asyncio
import base64
import logging

import edge_tts

logger = logging.getLogger(__name__)

_tts_semaphore = asyncio.Semaphore(2)
_BOUNDARIES = frozenset("。！？；.!?\n")
_MAX_BUFFER_LEN = 100


class SentenceBuffer:
    """Accumulate streaming text chunks; yield complete sentences at boundaries."""

    def __init__(self) -> None:
        self._buf = ""

    def append(self, chunk: str) -> list[str]:
        """Feed a chunk, return list of complete sentences (may be empty)."""
        self._buf += chunk
        sentences: list[str] = []

        while True:
            idx = -1
            for i, ch in enumerate(self._buf):
                if ch in _BOUNDARIES:
                    idx = i
                    break

            if idx >= 0:
                sentence = self._buf[: idx + 1].strip()
                self._buf = self._buf[idx + 1 :]
                if sentence:
                    sentences.append(sentence)
            elif len(self._buf) >= _MAX_BUFFER_LEN:
                sentence = self._buf.strip()
                self._buf = ""
                if sentence:
                    sentences.append(sentence)
                break
            else:
                break

        return sentences

    def flush(self) -> str | None:
        """Flush remaining buffer content (call at stream end)."""
        text = self._buf.strip()
        self._buf = ""
        return text or None


async def tts_synthesize(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes:
    """Synthesize text to MP3 bytes via edge-tts."""
    async with _tts_semaphore:
        communicate = edge_tts.Communicate(text, voice)
        audio_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
        return b"".join(audio_chunks)


async def synthesize_and_enqueue(
    sentence: str,
    index: int,
    queue: asyncio.Queue[tuple[int, bytes] | None],
    voice: str,
) -> None:
    """Synthesize one sentence and put (index, audio_bytes) into the queue."""
    try:
        audio = await tts_synthesize(sentence, voice)
        await queue.put((index, audio))
    except Exception:
        logger.warning("TTS synthesis failed for sentence %d: %s", index, sentence[:30], exc_info=True)


async def list_voices(locale_prefix: str = "zh-CN") -> list[dict]:
    """Return available voices from edge-tts for a given locale prefix."""
    voices = await edge_tts.list_voices()
    return [
        {"name": v["ShortName"], "gender": v["Gender"], "friendlyName": v["FriendlyName"]}
        for v in voices
        if v["Locale"].startswith(locale_prefix)
    ]


def encode_audio_event(index: int, audio_bytes: bytes) -> str:
    """Format an SSE audio event string."""
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    return f'event: audio\ndata: {{"audio": "{b64}", "index": {index}}}\n\n'
