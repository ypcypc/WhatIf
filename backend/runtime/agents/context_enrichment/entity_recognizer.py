from typing import Type

from runtime.agents.base import BaseLLMCaller
from runtime.agents.models import EntityRecognitionResult
import config


class EntityRecognizerAgent(BaseLLMCaller):

    @property
    def prompt_file(self) -> str:
        return "prompts/entity.txt"

    @property
    def response_model(self) -> Type[EntityRecognitionResult]:
        return EntityRecognitionResult

    def run(self, text: str, lorebook_content: str) -> EntityRecognitionResult:
        template = self.load_prompt()
        prompt = self.build_prompt(template, text=text)

        result = self.llm.generate_structured_with_cache(
            prompt=prompt,
            response_model=self.response_model,
            cached_content=lorebook_content,
            model=self.model_name,
            temperature=self.temperature,
            cache_ttl=config.LOREBOOK_CACHE_TTL,
            thinking_budget=self.thinking_budget,
            extra_params=self.extra_params or None,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
        )
        return result

    def build_prompt(self, template: str, *, text: str) -> str:
        return template.replace("{text}", text)
