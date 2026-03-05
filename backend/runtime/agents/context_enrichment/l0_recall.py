from typing import Type

from runtime.agents.base import BaseLLMCaller
from .formatters import format_l0_summaries
from runtime.agents.models import L0SelectionOutput, L0Summary


class L0RecallAgent(BaseLLMCaller):

    @property
    def prompt_file(self) -> str:
        return "prompts/l0_recall.txt"

    @property
    def response_model(self) -> Type[L0SelectionOutput]:
        return L0SelectionOutput

    def build_prompt(
        self,
        template: str,
        query: str,
        candidate_l0s: list[L0Summary],
    ) -> str:
        l0_text = format_l0_summaries(candidate_l0s)
        return (
            template
            .replace("{query}", query)
            .replace("{l0_summaries}", l0_text)
        )

    def select(
        self,
        query: str,
        candidate_l0s: list[L0Summary],
    ) -> L0SelectionOutput:
        template = self.load_prompt()
        prompt = self.build_prompt(template, query, candidate_l0s)
        return self.call_llm(prompt)
