from typing import Type

from core.models import NecessityData
from preprocessing.base import ValidatedExtractor
from preprocessing.entity_transition.validators import validate_necessity


class NecessityGrader(ValidatedExtractor):

    @property
    def prompt_file(self) -> str:
        return "necessity_grading.txt"

    @property
    def response_model(self) -> Type[NecessityData]:
        return NecessityData

    def build_prompt(
        self,
        template: str,
        events_json: str,
        candidates_json: str,
    ) -> str:
        return (
            template
            .replace("{events_json}", events_json)
            .replace("{candidates_json}", candidates_json)
        )

    def validate(self, result: NecessityData, **kwargs) -> list[str]:
        events_slim = kwargs.get("_events_slim", [])
        return validate_necessity(
            result.model_dump(),
            events_slim,
        )

    def extract(self, events_json: str, candidates_json: str, events_slim: list[dict] | None = None) -> NecessityData:
        return super().extract(
            events_json=events_json,
            candidates_json=candidates_json,
            _events_slim=events_slim or [],
        )
