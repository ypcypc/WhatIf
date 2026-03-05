import json
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


class WorldPkgLoader:

    def __init__(self, worldpkg_path: Path):
        self.path = worldpkg_path
        self._load_all()
        self._build_indices()

    def _load(self, model: type[T], rel_path: str) -> T:
        path = self.path / rel_path
        return model.model_validate_json(path.read_text(encoding="utf-8"))

    def _load_all(self) -> None:
        self.metadata = self._load(Metadata, "metadata.json")
        self.sentences = self._load(SentenceData, "source/sentences.json")
        self.events = self._load(EventData, "events/events.json")
        self.characters = self._load(CharacterData, "lorebook/characters.json")
        self.locations = self._load(LocationData, "lorebook/locations.json")
        self.items = self._load(ItemData, "lorebook/items.json")

        knowledge_path = self.path / "lorebook" / "knowledge.json"
        if knowledge_path.exists():
            self.knowledge = self._load(KnowledgeData, "lorebook/knowledge.json")
        else:
            self.knowledge = KnowledgeData(knowledge=[])

        transitions_path = self.path / "transitions" / "transitions.json"
        if transitions_path.exists():
            raw = json.loads(transitions_path.read_text(encoding="utf-8"))
            self.transitions: list[EventTransition] = [
                EventTransition.model_validate(t) for t in raw["transitions"]
            ]
        else:
            self.transitions: list[EventTransition] = []

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
