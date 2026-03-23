import json
import zipfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from core.models import (
    Metadata,
    SentenceData,
    Sentence,
    EventData,
    Event,
    EventPhaseDetail,
    CharacterData,
    Character,
    LocationData,
    ItemData,
    CharacterImportance,
    KnowledgeData,
    EventTransition,
    Precondition,
)

T = TypeVar("T", bound=BaseModel)

_MIME_MAP = {
    "webp": "image/webp",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


class WorldPkgLoader:

    def __init__(self, wpkg_path: Path):
        self.wpkg_path = wpkg_path
        self._load_all()
        self._build_indices()

    def _try_load(self, zf: zipfile.ZipFile, rel_path: str, model: type[T]) -> T | None:
        try:
            return model.model_validate_json(zf.read(rel_path))
        except KeyError:
            return None

    def _load_transitions(self, zf: zipfile.ZipFile) -> list[EventTransition]:
        try:
            raw = json.loads(zf.read("transitions/transitions.json"))
            return [EventTransition.model_validate(t) for t in raw["transitions"]]
        except KeyError:
            return []

    def _load_all(self) -> None:
        with zipfile.ZipFile(self.wpkg_path, "r") as zf:
            self.metadata = Metadata.model_validate_json(zf.read("metadata.json"))
            self.sentences = SentenceData.model_validate_json(zf.read("source/sentences.json"))
            self.events = EventData.model_validate_json(zf.read("events/events.json"))
            self.characters = CharacterData.model_validate_json(zf.read("lorebook/characters.json"))
            self.locations = LocationData.model_validate_json(zf.read("lorebook/locations.json"))
            self.items = ItemData.model_validate_json(zf.read("lorebook/items.json"))
            self.knowledge = self._try_load(zf, "lorebook/knowledge.json", KnowledgeData) or KnowledgeData(knowledge=[])
            self.transitions: list[EventTransition] = self._load_transitions(zf)

    def _build_indices(self) -> None:
        self._event_index: dict[str, Event] = {
            e.id: e for e in self.events.events
        }
        self._sentence_index: dict[int, Sentence] = {
            s.index: s for s in self.sentences.sentences
        }
        self._transition_index: dict[str, EventTransition] = {
            t.event_id: t for t in self.transitions
        }

    def get_event(self, event_id: str) -> Event | None:
        return self._event_index.get(event_id)

    def get_sentences_range(self, start: int, end: int) -> list[Sentence]:
        return [
            self._sentence_index[i]
            for i in range(start, end + 1)
            if i in self._sentence_index
        ]

    def get_sentences_text(self, start: int, end: int) -> str:
        sentences = self.get_sentences_range(start, end)
        return "".join(s.text for s in sentences)

    def get_event_text_full(self, event_id: str) -> str:
        event = self.get_event(event_id)
        if not event:
            raise ValueError(f"Event '{event_id}' not found")
        start, end = event.sentence_range
        return self.get_sentences_text(start, end)

    def get_event_text_decision(self, event_id: str) -> str:
        event = self.get_event(event_id)
        if not event:
            raise ValueError(f"Event '{event_id}' not found")
        if not event.decision_text:
            raise ValueError(f"Event '{event_id}' missing decision_text")
        return event.decision_text

    def get_protagonist(self) -> Character | None:
        for char in self.characters.characters:
            if char.importance == CharacterImportance.PROTAGONIST:
                return char
        return None

    def get_events_by_order(self) -> list[Event]:
        return sorted(
            self.events.events,
            key=lambda e: e.sentence_range[0] if e.sentence_range else float('inf')
        )

    def get_first_event(self) -> Event | None:
        ordered = self.get_events_by_order()
        return ordered[0] if ordered else None

    def get_next_event_id(self, current_event_id: str) -> str | None:
        ordered = self.get_events_by_order()
        for i, event in enumerate(ordered):
            if event.id == current_event_id and i + 1 < len(ordered):
                return ordered[i + 1].id
        return None

    def get_phase(self, event_id: str, phase_name: str) -> EventPhaseDetail | None:
        event = self.get_event(event_id)
        if not event or not event.phases:
            return None
        return event.phases.get(phase_name)

    def get_phase_text_full(self, event_id: str, phase_name: str) -> str:
        phase = self.get_phase(event_id, phase_name)
        if not phase or not phase.sentence_range:
            raise ValueError(f"Event '{event_id}' phase '{phase_name}' not found or has no sentence_range")
        start, end = phase.sentence_range
        return self.get_sentences_text(start, end)

    def get_phase_text_decision(self, event_id: str, phase_name: str) -> str:
        phase = self.get_phase(event_id, phase_name)
        if not phase:
            raise ValueError(f"Event '{event_id}' phase '{phase_name}' not found")
        if not phase.decision_text:
            raise ValueError(f"Event '{event_id}' phase '{phase_name}' missing decision_text")
        return phase.decision_text

    def get_transition(self, event_id: str) -> EventTransition | None:
        return self._transition_index.get(event_id)

    def get_preconditions(self, event_id: str) -> list[Precondition]:
        transition = self.get_transition(event_id)
        return transition.preconditions if transition else []

    def get_event_image(self, event_id: str) -> tuple[bytes, str] | None:
        """按需读取图片，临时打开 ZipFile。返回 (bytes, media_type) 或 None。"""
        event = self.get_event(event_id)
        if not event or not event.image:
            return None
        with zipfile.ZipFile(self.wpkg_path, "r") as zf:
            try:
                data = zf.read(event.image)
            except KeyError:
                return None
        ext = event.image.rsplit(".", 1)[-1].lower()
        media_type = _MIME_MAP.get(ext, "application/octet-stream")
        return data, media_type

    def get_lorebook_raw(self) -> dict:
        """返回已解析的 lorebook 数据，供 LorebookQuery 使用。"""
        return {
            "characters": self.characters,
            "locations": self.locations,
            "items": self.items,
            "knowledge": self.knowledge,
        }
