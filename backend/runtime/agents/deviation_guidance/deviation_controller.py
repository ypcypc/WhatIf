from typing import Type

from core.models import EventImportance
from runtime.agents.base import BaseLLMCaller
from runtime.agents.models import DeviationControlOutput, HistoryEntry


class DeviationController(BaseLLMCaller):

    @property
    def prompt_file(self) -> str:
        return "prompts/deviation_analysis.txt"

    @property
    def response_model(self) -> Type[DeviationControlOutput]:
        return DeviationControlOutput

    def build_prompt(
        self,
        template: str,
        event_id: str,
        history: list[HistoryEntry],
        goal: str,
        player_input: str,
        importance: EventImportance,
        context: str,
        delta_context: str = "",
    ) -> str:
        return (
            template
            .replace("{event_id}", event_id)
            .replace("{history}", self._format_history(history))
            .replace("{goal}", goal)
            .replace("{player_input}", player_input)
            .replace("{importance}", importance.value)
            .replace("{context}", context)
            .replace("{delta_context}", delta_context)
        )

    def _format_history(self, history: list[HistoryEntry]) -> str:
        if not history:
            return "<empty/>"
        lines = []
        for i, entry in enumerate(history, 1):
            lines.append(f"<turn_{i}>")
            lines.append(f"  <player>{entry.player_input}</player>")
            if entry.response_summary:
                lines.append(f"  <response>{entry.response_summary}</response>")
            lines.append(f"</turn_{i}>")
        return "\n".join(lines)

    def analyze(
        self,
        event_id: str,
        history: list[HistoryEntry],
        goal: str,
        player_input: str,
        importance: EventImportance,
        context: str,
        delta_context: str = "",
    ) -> DeviationControlOutput:
        template = self.load_prompt()
        prompt = self.build_prompt(
            template=template,
            event_id=event_id,
            history=history,
            goal=goal,
            player_input=player_input,
            importance=importance,
            context=context,
            delta_context=delta_context,
        )
        return self.call_llm(prompt)
