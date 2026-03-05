from typing import Type

from core.llm import LLMClient
from runtime.agents.base import BaseLLMCaller
from runtime.agents.models import L0Summary, L1Response, L1Summary


class L1Compressor(BaseLLMCaller):

    COMPRESSION_RATIO = 0.3

    def __init__(self, llm_client: LLMClient, protagonist_name: str = ""):
        super().__init__(llm_client)
        self._protagonist_name = protagonist_name

    @property
    def prompt_file(self) -> str:
        return "prompts/l1_compress.txt"

    @property
    def response_model(self) -> Type[L1Response]:
        return L1Response

    def build_prompt(self, template: str, l1_id: str, l0_summaries: list[L0Summary]) -> str:
        event_ids = [s.event_id for s in l0_summaries]

        l0_total_char_count = sum(len(s.summary) for s in l0_summaries)
        min_summary_length = int(l0_total_char_count * self.COMPRESSION_RATIO)

        l0_tag_parts = []
        for s in l0_summaries:
            l0_tag_parts.append(
                f'<l0 event_id="{s.event_id}">\n'
                f'<summary>{s.summary}</summary>\n'
                f'<tags>{s.tags}</tags>\n'
                f'</l0>'
            )

        return (template
            .replace("{l1_id}", l1_id)
            .replace("{l0_count}", str(len(l0_summaries)))
            .replace("{start_id}", event_ids[0])
            .replace("{end_id}", event_ids[-1])
            .replace("{l0_total_char_count}", str(l0_total_char_count))
            .replace("{min_summary_length}", str(min_summary_length))
            .replace("{l0_summaries}", "\n".join(l0_tag_parts))
            .replace("{protagonist_name}", self._protagonist_name))

    def compress(self, l1_id: str, l0_summaries: list[L0Summary]) -> L1Summary:
        prompt = self.build_prompt(self.load_prompt(), l1_id, l0_summaries)
        response: L1Response = self.call_llm(prompt)
        event_ids = [s.event_id for s in l0_summaries]
        return L1Summary(
            id=l1_id,
            covers=f"{event_ids[0]}-{event_ids[-1]}",
            summary=response.summary,
            tags=response.tags,
            char_count=sum(s.char_count for s in l0_summaries),
            l0_summaries=l0_summaries,
        )
