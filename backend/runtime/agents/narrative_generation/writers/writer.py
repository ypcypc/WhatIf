from pydantic import BaseModel

from runtime.agents.base import BaseLLMCaller


class WriterInput(BaseModel):
    phase_source: str
    writing_guidance: str


class UnifiedWriter(BaseLLMCaller):

    writer_type = "unified"

    @property
    def prompt_file(self) -> str:
        return "prompt.txt"

    @property
    def response_model(self):
        return None

    def __init__(self, llm_client, protagonist_name="", protagonist_aliases=None):
        super().__init__(llm_client)
        self.protagonist_name = protagonist_name
        aliases = protagonist_aliases or []
        aliases_str = "、".join(aliases) if aliases else "无"
        self._system_prompt = (
            self.load_prompt()
            .replace("{protagonist}", protagonist_name or "主角")
            .replace("{protagonist_aliases}", aliases_str)
        )

    def generate(self, inp: WriterInput, on_chunk=None) -> str:
        prompt = self._build_prompt(inp)
        if on_chunk:
            narrative = self.call_llm_text_stream(prompt, on_chunk)
        else:
            narrative = self.call_llm_text(prompt)

        self.log_generation(
            writer_type=self.writer_type,
            input_data=inp,
            output_text=narrative,
            prompt=prompt,
        )
        return narrative

    def _build_prompt(self, inp: WriterInput) -> str:
        parts = [self._system_prompt]
        if inp.phase_source:
            parts.append(f"<phase_source>\n{inp.phase_source}\n</phase_source>")
        parts.append(f"<writing_guidance>\n{inp.writing_guidance}\n</writing_guidance>")
        return "\n\n".join(parts)
