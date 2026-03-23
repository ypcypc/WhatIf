"""Voice configuration endpoints."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.tts import list_voices

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/voices")
async def get_voices(locale: str = Query("zh-CN")):
    """Return available TTS voices for a locale."""
    voices = await list_voices(locale)
    return {"voices": voices}


class SegmentRequest(BaseModel):
    text: str


@router.post("/segment")
async def segment_text(req: SegmentRequest):
    """Segment raw voice transcript into readable clauses using spaCy."""
    import spacy

    _nlp_cache: list = getattr(segment_text, "_nlp_cache", [])
    if not _nlp_cache:
        _nlp_cache.append(spacy.load("zh_core_web_sm"))
        segment_text._nlp_cache = _nlp_cache  # type: ignore[attr-defined]

    nlp = _nlp_cache[0]
    doc = nlp(req.text.strip())
    segments = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    return {"segmented": " ".join(segments)}
