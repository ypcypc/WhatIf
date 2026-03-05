import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel

from core.llm import LLMClient
import config

T = TypeVar("T", bound=BaseModel)


class BaseExtractor(ABC):

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        config_name = config.class_to_config_name(self.__class__.__name__)
        self._config = config.get_llm_config(config_name)

    @property
    @abstractmethod
    def prompt_file(self) -> str: ...

    @property
    @abstractmethod
    def response_model(self) -> Type[T]: ...

    @abstractmethod
    def build_prompt(self, template: str, **kwargs) -> str: ...

    @property
    def model_name(self) -> str:
        return self._config.model

    @property
    def thinking_budget(self) -> int | None:
        return self._config.thinking_budget if self._config.thinking_budget else None

    @property
    def temperature(self) -> float:
        return self._config.temperature

    @property
    def extra_params(self) -> dict:
        return self._config.extra_params

    @property
    def api_base(self) -> str | None:
        return self._config.api_base

    @property
    def api_key_env(self) -> str | None:
        return self._config.api_key_env

    def load_prompt(self) -> str:
        module = sys.modules[self.__class__.__module__]
        prompts_dir = Path(module.__file__).parent / "prompts"
        return (prompts_dir / self.prompt_file).read_text(encoding="utf-8")

    def extract(self, **kwargs) -> T:
        prompt_template = self.load_prompt()
        prompt = self.build_prompt(prompt_template, **kwargs)

        print(f"  [{self.__class__.__name__}] 调用 {self.model_name}...")

        result = self.llm.generate_structured(
            prompt=prompt,
            response_model=self.response_model,
            model=self.model_name,
            temperature=self.temperature,
            thinking_budget=self.thinking_budget,
            extra_params=self.extra_params or None,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
        )

        print(f"  [{self.__class__.__name__}] 完成")
        return result


class ValidatedExtractor(BaseExtractor):

    MAX_RETRIES = 2

    @abstractmethod
    def validate(self, result: T, **kwargs) -> list[str]: ...

    def build_repair_prompt(
        self, template: str, result: T, errors: list[str], **kwargs
    ) -> str:
        original = self.build_prompt(template, **kwargs)
        error_text = "\n".join(f"- {e}" for e in errors)
        return (
            f"{original}\n\n"
            f"【上次输出有以下错误，请修正后重新输出完整结果】\n"
            f"{error_text}"
        )

    def extract(self, **kwargs) -> T:
        template = self.load_prompt()
        prompt_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("_")}
        prompt = self.build_prompt(template, **prompt_kwargs)
        name = self.__class__.__name__
        best_result: T | None = None
        best_error_count = float("inf")

        for attempt in range(1 + self.MAX_RETRIES):
            label = f"(重试 {attempt})" if attempt > 0 else ""
            print(f"  [{name}] 调用 {self.model_name} {label}...".rstrip())

            result = self.llm.generate_structured(
                prompt=prompt,
                response_model=self.response_model,
                model=self.model_name,
                temperature=self.temperature,
                thinking_budget=self.thinking_budget,
                extra_params=self.extra_params or None,
                api_base=self.api_base,
                api_key_env=self.api_key_env,
            )

            errors = self.validate(result, **kwargs)
            if not errors:
                print(f"  [{name}] 完成（验证通过）")
                return result

            if len(errors) < best_error_count:
                best_result = result
                best_error_count = len(errors)

            print(f"  [{name}] 验证发现 {len(errors)} 个错误，准备重试...")
            for e in errors[:5]:
                print(f"    · {e}")
            if len(errors) > 5:
                print(f"    · ...还有 {len(errors) - 5} 个错误")

            prompt = self.build_repair_prompt(template, result, errors, **prompt_kwargs)

        print(f"  [{name}] 重试 {self.MAX_RETRIES} 次后仍有错误（最少 {best_error_count} 个），返回最佳结果")
        return best_result
