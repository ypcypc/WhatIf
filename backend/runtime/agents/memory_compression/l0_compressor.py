from typing import Type

from core.llm import LLMClient
from runtime.agents.base import BaseLLMCaller
from runtime.agents.models import L0Response, L0Summary


class L0Compressor(BaseLLMCaller):

    COMPRESSION_RATIO = 0.3

    def __init__(self, llm_client: LLMClient, protagonist_name: str = ""):
        super().__init__(llm_client)
        self._protagonist_name = protagonist_name

    @property
    def prompt_file(self) -> str:
        return "prompts/l0_compress.txt"

    @property
    def response_model(self) -> Type[L0Response]:
        return L0Response

    def build_prompt(self, template: str, event_id: str, original_text: str) -> str:
        char_count = len(original_text)
        min_summary_length = int(char_count * self.COMPRESSION_RATIO)
        return (template
            .replace("{event_id}", event_id)
            .replace("{original_text}", original_text)
            .replace("{original_char_count}", str(char_count))
            .replace("{min_summary_length}", str(min_summary_length))
            .replace("{protagonist_name}", self._protagonist_name))

    def compress(self, event_id: str, original_text: str) -> L0Summary:
        prompt = self.build_prompt(self.load_prompt(), event_id, original_text)
        response: L0Response = self.call_llm(prompt)
        return L0Summary(
            event_id=event_id,
            summary=response.summary,
            tags=response.tags,
            char_count=len(original_text),
        )
