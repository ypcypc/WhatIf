from pathlib import Path

import tiktoken

import config


class TokenEstimator:

    def __init__(self, safety_factor: float | None = None):
        self._encoder = tiktoken.get_encoding("cl100k_base")
        self._safety_factor = (
            safety_factor or config.STAGE3_TOKEN_BUDGET.safety_factor
        )

    def count_tokens(self, text: str) -> int:
        return len(self._encoder.encode(text))

    def effective_budget(self, raw_budget: int) -> int:
        return int(raw_budget * self._safety_factor)


def compute_fixed_costs(estimator: TokenEstimator) -> dict[str, int]:
    prompt_dir = Path(__file__).parent / "prompts"

    templates = {
        "necessity_grader": "necessity_grading.txt",
        "transition_annotator": "transition_annotation.txt",
        "cross_validator": "cross_validation.txt",
        "repairer": "repair.txt",
    }

    placeholders = {
        "necessity_grader": ["{events_json}", "{candidates_json}"],
        "transition_annotator": [
            "{events_json}",
            "{necessary_json}",
            "{registry_json}",
        ],
        "cross_validator": [
            "{events_json}",
            "{transitions_draft_json}",
            "{registry_json}",
            "{pre_check_hints}",
        ],
        "repairer": [
            "{problematic_transitions}",
            "{validation_report}",
            "{registry_json}",
        ],
    }

    costs: dict[str, int] = {}
    for name, filename in templates.items():
        template_text = (prompt_dir / filename).read_text(encoding="utf-8")
        for ph in placeholders[name]:
            template_text = template_text.replace(ph, "")
        costs[name] = estimator.count_tokens(template_text)

    return costs
