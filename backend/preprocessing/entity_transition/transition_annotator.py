from typing import Type

from core.models import TransitionData
from preprocessing.base import ValidatedExtractor
from preprocessing.entity_transition.validators import validate_transitions


class TransitionAnnotator(ValidatedExtractor):

    @property
    def prompt_file(self) -> str:
        return "transition_annotation.txt"

    @property
    def response_model(self) -> Type[TransitionData]:
        return TransitionData

    def build_prompt(
        self,
        template: str,
        events_json: str,
        necessary_json: str,
        registry_json: str,
    ) -> str:
        return (
            template
            .replace("{events_json}", events_json)
            .replace("{necessary_json}", necessary_json)
            .replace("{registry_json}", registry_json)
        )

    def validate(self, result: TransitionData, **kwargs) -> list[str]:
        registry = kwargs.get("_registry", {})
        transitions_dicts = [
            {
                "event_id": t.event_id,
                "preconditions": [
                    p.model_dump(by_alias=True) for p in t.preconditions
                ],
                "effects": [
                    e.model_dump(by_alias=True) for e in t.effects
                ],
            }
            for t in result.transitions
        ]
        return validate_transitions(transitions_dicts, registry)

    def extract(
        self,
        events_json: str,
        necessary_json: str,
        registry_json: str,
        registry: dict | None = None,
    ) -> TransitionData:
        return super().extract(
            events_json=events_json,
            necessary_json=necessary_json,
            registry_json=registry_json,
            _registry=registry or {},
        )
