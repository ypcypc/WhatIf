import json
import os
from functools import lru_cache
from typing import Type, TypeVar, Iterator

import json_repair
import litellm
from litellm import completion, get_supported_openai_params, supports_response_schema
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

import config

load_dotenv()

litellm.drop_params = False

try:
    from runtime.game_logger import glog as _glog
except Exception:
    _glog = None

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=64)
def _check_native_schema(model: str, custom_provider: str | None) -> bool:
    try:
        supported = get_supported_openai_params(model=model, custom_llm_provider=custom_provider) or []
        if "response_format" not in supported:
            return False
        return bool(supports_response_schema(model=model, custom_llm_provider=custom_provider))
    except Exception:
        return False


_MODEL_MAX_OUTPUT: dict[str, int] = {
    "dashscope/qwen-max-latest": 8192,
    "dashscope/qwen-max": 8192,
}


class LLMClient:

    def __init__(self):
        pass

    @staticmethod
    def _budget_to_effort(thinking_budget: int | None) -> str | None:
        if thinking_budget is None or thinking_budget == 0:
            return None
        if thinking_budget == -1:
            return "medium"
        if thinking_budget <= 256:
            return "low"
        if thinking_budget <= 2048:
            return "medium"
        return "high"

    def _build_reasoning_params(
        self,
        model: str,
        thinking_budget: int | None,
        extra_params: dict | None,
    ) -> dict:
        if extra_params:
            return extra_params

        prefix = model.split("/", 1)[0] if "/" in model else ""

        if prefix == "dashscope":
            if thinking_budget and thinking_budget != 0:
                params: dict = {"enable_thinking": True}
                if thinking_budget > 0:
                    params["thinking_budget"] = thinking_budget
                return {"extra_body": params}
            return {"extra_body": {"enable_thinking": False}}

        if thinking_budget is None or thinking_budget == 0:
            return {}

        if prefix == "anthropic":
            budget = max(1024, thinking_budget if thinking_budget > 0 else 2048)
            return {"thinking": {"type": "enabled", "budget_tokens": budget}}

        return {"reasoning_effort": self._budget_to_effort(thinking_budget)}

    def _needs_prompt_only_json(self, model: str) -> bool:
        cp = model.split("/", 1)[0] if "/" in model else None
        return not _check_native_schema(model, cp)

    def _load_json_system_template(self) -> str:
        template_path = config.CORE_PROMPTS_DIR / "json_output_system.txt"
        return template_path.read_text(encoding="utf-8")

    def _build_json_system_prompt(self, response_model: Type[T]) -> str:
        template = self._load_json_system_template()
        schema = response_model.model_json_schema()
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        return template.replace("{schema_str}", schema_str)

    def _clean_json_response(self, content: str) -> str:
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    def _parse_or_repair(self, content: str, response_model: type[T]) -> T:
        try:
            return response_model.model_validate_json(content)
        except ValidationError:
            if _glog:
                _glog.log("LLM_JSON_REPAIR", {
                    "model": response_model.__name__,
                    "content_preview": content[:200],
                })
            repaired = json_repair.repair_json(content)
            return response_model.model_validate_json(repaired)

    def generate(
        self,
        prompt: str,
        model: str = "dashscope/qwen3.5-flash",
        temperature: float = 0.3,
        thinking_budget: int | None = None,
        extra_params: dict | None = None,
        api_base: str | None = None,
        api_key_env: str | None = None,
        log: bool = True,
    ) -> str:
        params = self._build_reasoning_params(model, thinking_budget, extra_params)

        call_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            **params,
        }
        if api_base:
            call_params["api_base"] = api_base
        if api_key_env:
            call_params["api_key"] = os.getenv(api_key_env)

        response = completion(**call_params)
        result = response.choices[0].message.content

        if _glog and log:
            _glog.log("LLM_CALL", {
                "method": "generate",
                "model": model,
                "temperature": temperature,
                "thinking_budget": thinking_budget,
                "extra_params": extra_params,
                "prompt_len": len(prompt),
                "response_len": len(result) if result else 0,
                "prompt": prompt,
                "response": result,
            })

        return result

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        model: str = "dashscope/qwen3.5-flash",
        temperature: float = 0.2,
        thinking_budget: int | None = None,
        extra_params: dict | None = None,
        api_base: str | None = None,
        api_key_env: str | None = None,
        max_tokens: int = 32768,
    ) -> T:
        params = self._build_reasoning_params(model, thinking_budget, extra_params)

        use_prompt_only = self._needs_prompt_only_json(model)

        model_cap = _MODEL_MAX_OUTPUT.get(model)
        if model_cap and max_tokens > model_cap:
            max_tokens = model_cap

        if use_prompt_only:
            system_prompt = self._build_json_system_prompt(response_model)
            call_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                **params,
            }
        else:
            call_params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_model,
                **params,
            }

        if api_base:
            call_params["api_base"] = api_base
        if api_key_env:
            call_params["api_key"] = os.getenv(api_key_env)

        response = completion(**call_params)
        content = response.choices[0].message.content

        if use_prompt_only:
            content = self._clean_json_response(content)

        parsed = self._parse_or_repair(content, response_model)

        if _glog:
            _glog.log("LLM_CALL", {
                "method": "generate_structured",
                "model": model,
                "temperature": temperature,
                "thinking_budget": thinking_budget,
                "extra_params": extra_params,
                "response_model": response_model.__name__,
                "prompt_len": len(prompt),
                "response_len": len(content) if content else 0,
                "prompt": prompt,
                "response": content,
                "parsed": parsed.model_dump(),
            })

        return parsed

    def generate_stream(
        self,
        prompt: str,
        model: str = "dashscope/qwen3.5-flash",
        temperature: float = 0.3,
        thinking_budget: int | None = None,
        extra_params: dict | None = None,
        api_base: str | None = None,
        api_key_env: str | None = None,
    ) -> Iterator[str]:
        params = self._build_reasoning_params(model, thinking_budget, extra_params)

        call_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": True,
            **params,
        }
        if api_base:
            call_params["api_base"] = api_base
        if api_key_env:
            call_params["api_key"] = os.getenv(api_key_env)

        response = completion(**call_params)
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate_structured_with_cache(
        self,
        prompt: str,
        response_model: Type[T],
        cached_content: str,
        model: str = "dashscope/qwen3.5-flash",
        temperature: float = 0.2,
        cache_ttl: str = "3600s",
        thinking_budget: int | None = None,
        extra_params: dict | None = None,
        api_base: str | None = None,
        api_key_env: str | None = None,
    ) -> T:
        params = self._build_reasoning_params(model, thinking_budget, extra_params)

        use_prompt_only = self._needs_prompt_only_json(model)

        if use_prompt_only:
            json_system = self._build_json_system_prompt(response_model)
            combined_system = f"{cached_content}\n\n{json_system}"
            messages = [
                {"role": "system", "content": combined_system},
                {"role": "user", "content": prompt},
            ]
            call_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **params,
            }
        else:
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": cached_content,
                            "cache_control": {"type": "ephemeral", "ttl": cache_ttl},
                        }
                    ],
                },
                {"role": "user", "content": prompt},
            ]
            call_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "response_format": response_model,
                **params,
            }

        if api_base:
            call_params["api_base"] = api_base
        if api_key_env:
            call_params["api_key"] = os.getenv(api_key_env)

        response = completion(**call_params)
        content = response.choices[0].message.content

        if use_prompt_only:
            content = self._clean_json_response(content)

        parsed = self._parse_or_repair(content, response_model)

        if _glog:
            _glog.log("LLM_CALL", {
                "method": "generate_structured_with_cache",
                "model": model,
                "temperature": temperature,
                "extra_params": extra_params,
                "response_model": response_model.__name__,
                "prompt_len": len(prompt),
                "cached_content_len": len(cached_content),
                "response_len": len(content) if content else 0,
                "prompt": prompt,
                "response": content,
                "parsed": parsed.model_dump(),
            })

        return parsed
