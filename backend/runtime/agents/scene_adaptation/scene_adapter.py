from runtime.agents.base import BaseLLMCaller
from runtime.agents.models import AdaptationPlan
from runtime.agents.delta_state import DeltaEntry


class SceneAdapter(BaseLLMCaller):

    prompt_file = "prompts/scene_adapter.txt"
    response_model = AdaptationPlan

    def adapt(
        self,
        event_id: str,
        event_original_text: str,
        active_deltas: list[DeltaEntry],
        archived_overrides_text: str = "",
    ) -> AdaptationPlan:
        template = self.load_prompt()
        prompt = self._build_prompt(
            template,
            event_id=event_id,
            event_original_text=event_original_text,
            active_deltas=active_deltas,
            archived_overrides_text=archived_overrides_text,
        )
        return self.call_llm(prompt)

    def _build_prompt(self, template: str, **kwargs) -> str:
        deltas = kwargs["active_deltas"]
        delta_lines = []
        for d in deltas:
            delta_lines.append(
                f'<delta id="{d.delta_id}" intensity="{d.intensity}" '
                f'source_event="{d.source_event}">{d.fact}</delta>'
            )

        return (
            template
            .replace("{event_id}", kwargs["event_id"])
            .replace("{event_original_text}", kwargs["event_original_text"])
            .replace("{active_deltas}", "\n".join(delta_lines) or "无")
            .replace("{archived_overrides}", kwargs["archived_overrides_text"] or "无")
        )
