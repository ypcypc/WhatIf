import json
from typing import Type

from core.models import TransitionData
from preprocessing.base import BaseExtractor


class Repairer(BaseExtractor):

    @property
    def prompt_file(self) -> str:
        return "repair.txt"

    @property
    def response_model(self) -> Type[TransitionData]:
        return TransitionData

    def build_prompt(
        self,
        template: str,
        problematic_transitions: str,
        validation_report: str,
        registry_json: str,
    ) -> str:
        return (
            template
            .replace("{problematic_transitions}", problematic_transitions)
            .replace("{validation_report}", validation_report)
            .replace("{registry_json}", registry_json)
        )

    def extract(
        self,
        problematic_events: list[dict],
        validation_reports: list[dict],
        registry_json: str,
    ) -> TransitionData:
        return super().extract(
            problematic_transitions=json.dumps(
                problematic_events, ensure_ascii=False, indent=2
            ),
            validation_report=json.dumps(
                validation_reports, ensure_ascii=False, indent=2
            ),
            registry_json=registry_json,
        )


def merge_repairs(
    draft: list[dict],
    repairs: TransitionData,
) -> list[dict]:
    repair_map = {t.event_id: t for t in repairs.transitions}

    merged = []
    for event in draft:
        eid = event["event_id"]
        if eid in repair_map:
            repaired = repair_map[eid]
            merged.append({
                "event_id": repaired.event_id,
                "preconditions": [
                    p.model_dump(by_alias=True) for p in repaired.preconditions
                ],
                "effects": [
                    e.model_dump(by_alias=True) for e in repaired.effects
                ],
            })
        else:
            merged.append(event)

    return merged
