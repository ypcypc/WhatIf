from typing import Type

from core.models import EventData, SentenceData
from preprocessing.base import BaseExtractor


class EventExtractor(BaseExtractor):

    @property
    def prompt_file(self) -> str:
        return "event_extraction.txt"

    @property
    def response_model(self) -> Type[EventData]:
        return EventData

    def build_prompt(self, template: str, sentences: SentenceData) -> str:
        sentences_json = self._build_sentences_json(sentences)
        return template.replace("{sentences_json}", sentences_json)

    def _build_sentences_json(self, sentences: SentenceData) -> str:
        import json
        data = [{"id": s.index, "text": s.text} for s in sentences.sentences]
        return json.dumps(data, ensure_ascii=False, indent=2)
