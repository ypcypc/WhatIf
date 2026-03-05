from runtime.agents.base import BaseLLMCaller
from runtime.agents.models import BridgeResult
from runtime.agents.delta_state import DeltaEntry


class BridgePlanner(BaseLLMCaller):

    prompt_file = "prompts/bridge_planner.txt"
    response_model = BridgeResult

    def plan(
        self,
        premise_conflicts: list[dict],
        active_deltas: list[DeltaEntry],
        previous_event: str,
        next_phase_source: str,
        preconditions: list[dict],
    ) -> BridgeResult:
        template = self.load_prompt()
        prompt = self.build_prompt(
            template,
            premise_conflicts=premise_conflicts,
            active_deltas=active_deltas,
            previous_event=previous_event,
            next_phase_source=next_phase_source,
            preconditions=preconditions,
        )
        return self.call_llm(prompt)

    def build_prompt(self, template: str, **kwargs) -> str:
        conflicts = kwargs["premise_conflicts"]
        deltas = kwargs["active_deltas"]
        delta_map = {d.delta_id: d for d in deltas}

        conflict_lines = []
        for c in conflicts:
            delta = delta_map.get(c["delta_id"])
            if not delta:
                continue
            conflict_lines.append(
                f'<conflict delta_id="{delta.delta_id}" '
                f'fact="{delta.fact}" intensity="{delta.intensity}" '
                f'source_event="{delta.source_event}">\n'
                f'  <conflicting_premise>{c["conflicting_premise"]}</conflicting_premise>\n'
                f'  <reason>{c["conflict_reason"]}</reason>\n'
                f'</conflict>'
            )

        precondition_lines = [
            f'- {p["name"]}（{p["type"]}）的{p["attribute"]}必须为 {p["from"]}'
            for p in kwargs["preconditions"]
            if p.get("from") is not None
        ]

        return (
            template
            .replace("{conflicts}", "\n".join(conflict_lines))
            .replace("{previous_event}", kwargs["previous_event"] or "")
            .replace("{next_phase_source}", kwargs["next_phase_source"])
            .replace("{preconditions}", "\n".join(precondition_lines) or "无")
        )
