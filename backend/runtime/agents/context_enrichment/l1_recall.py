from typing import Type

from runtime.agents.base import BaseLLMCaller
from .formatters import format_l0_summaries, format_l1_summaries
from runtime.agents.models import L1SelectionOutput, L0Summary, L1Summary


class L1RecallAgent(BaseLLMCaller):

    @property
    def prompt_file(self) -> str:
        return "prompts/l1_recall.txt"

    @property
    def response_model(self) -> Type[L1SelectionOutput]:
        return L1SelectionOutput

    def build_prompt(
        self,
        template: str,
        query: str,
        l1_summaries: list[L1Summary],
        pending_l0s: list[L0Summary],
    ) -> str:
        l1_text = format_l1_summaries(l1_summaries)
        pending_text = format_l0_summaries(pending_l0s)
        return (
            template
            .replace("{query}", query)
            .replace("{l1_summaries}", l1_text)
            .replace("{pending_l0s}", pending_text)
        )

    def select(
        self,
        query: str,
        l1_summaries: list[L1Summary],
        pending_l0s: list[L0Summary],
    ) -> L1SelectionOutput:
        template = self.load_prompt()
        prompt = self.build_prompt(template, query, l1_summaries, pending_l0s)
        return self.call_llm(prompt)
