import json
from typing import Type

from core.models import ValidationReport
from preprocessing.base import BaseExtractor


class CrossValidator(BaseExtractor):

    @property
    def prompt_file(self) -> str:
        return "cross_validation.txt"

    @property
    def response_model(self) -> Type[ValidationReport]:
        return ValidationReport

    def build_prompt(
        self,
        template: str,
        events_json: str,
        transitions_draft_json: str,
        registry_json: str,
        necessary_json: str,
        pre_check_hints: str = "",
    ) -> str:
        return (
            template
            .replace("{events_json}", events_json)
            .replace("{transitions_draft_json}", transitions_draft_json)
            .replace("{registry_json}", registry_json)
            .replace("{necessary_json}", necessary_json)
            .replace("{pre_check_hints}", pre_check_hints)
        )

    def extract(
        self,
        events_json: str,
        transitions_draft: list[dict],
        events_slim: list[dict],
        registry_json: str,
        necessary_json: str,
    ) -> ValidationReport:
        transitions_draft_json = json.dumps(
            transitions_draft, ensure_ascii=False, indent=2
        )

        return super().extract(
            events_json=events_json,
            transitions_draft_json=transitions_draft_json,
            registry_json=registry_json,
            necessary_json=necessary_json,
            pre_check_hints="",
        )
