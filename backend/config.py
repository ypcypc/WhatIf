import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

load_dotenv()


class LLMConfig(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    model: str
    temperature: float = 0.2
    thinking_budget: int = 0
    extra_params: dict[str, Any] = Field(default_factory=dict)
    api_base: str | None = None
    api_key_env: str | None = None

    @model_validator(mode="after")
    def _check_reserved_keys(self) -> "LLMConfig":
        reserved = {"model", "messages", "temperature", "stream", "response_format", "max_tokens"}
        conflict = reserved & self.extra_params.keys()
        if conflict:
            raise ValueError(f"extra_params 不允许覆盖保留键: {conflict}")
        return self


_REQUIRED_KEYS = frozenset({
    "event_extractor", "lorebook_extractor", "decision_text_extractor",
    "necessity_grader", "transition_annotator", "cross_validator", "repairer",
    "unified_writer", "setup_orchestrator", "confrontation_orchestrator",
    "resolution_orchestrator", "bridge_planner", "deviation_controller",
    "l0_recall_agent", "l1_recall_agent", "entity_recognizer_agent",
    "l0_compressor", "l1_compressor", "scene_adapter",
})

_PROVIDER_KEY_MAP = {
    "dashscope": "DASHSCOPE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "volcengine": "VOLCENGINE_API_KEY",
}

PROJECT_ROOT = Path(__file__).parent
REPO_ROOT = PROJECT_ROOT.parent
OUTPUT_DIR = REPO_ROOT / "output"
OUTPUT_BASE = OUTPUT_DIR / "龙族"
CORE_PROMPTS_DIR = PROJECT_ROOT / "core" / "prompts"
SAVES_DIR = REPO_ROOT / "saves"

SESSION_LOG_ENABLED = True
SESSION_LOG_DIR = REPO_ROOT / "logs" / "sessions"
SESSION_LOG_CATEGORIES: set[str] | str = "ALL"

LOREBOOK_CACHE_TTL = "3600s"


def _load_llm_configs() -> dict[str, LLMConfig]:
    config_path = PROJECT_ROOT / "llm_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"LLM 配置文件不存在: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    allowed_sections = {"extractors", "agents"}
    unknown_sections = set(raw.keys()) - allowed_sections
    if unknown_sections:
        raise ValueError(f"llm_config.yaml 存在未知顶层键: {unknown_sections}")

    configs: dict[str, LLMConfig] = {}
    for section in allowed_sections:
        for name, params in raw.get(section, {}).items():
            configs[name] = LLMConfig(**params)

    missing = _REQUIRED_KEYS - configs.keys()
    if missing:
        raise ValueError(f"llm_config.yaml 缺少必需配置: {missing}")
    extra = configs.keys() - _REQUIRED_KEYS
    if extra:
        raise ValueError(f"llm_config.yaml 存在未知配置键: {extra}")

    return configs


def _validate_api_keys(configs: dict[str, LLMConfig]) -> None:
    checked: set[str] = set()
    for cfg in configs.values():
        if cfg.api_key_env:
            env_var = cfg.api_key_env
        else:
            prefix = cfg.model.split("/", 1)[0] if "/" in cfg.model else ""
            env_var = _PROVIDER_KEY_MAP.get(prefix)
        if env_var and env_var not in checked:
            checked.add(env_var)
            if not os.getenv(env_var):
                raise ValueError(f"环境变量 {env_var} 未设置（模型 {cfg.model} 需要）")


_LLM_CONFIGS = _load_llm_configs()
_validate_api_keys(_LLM_CONFIGS)


def class_to_config_name(class_name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()


def get_llm_config(name: str) -> LLMConfig:
    if name not in _LLM_CONFIGS:
        raise KeyError(f"LLM 配置 '{name}' 未在 llm_config.yaml 中定义")
    return _LLM_CONFIGS[name]


@dataclass(frozen=True)
class TokenBudgetConfig:
    necessity_grader: int = 60_000
    transition_annotator: int = 70_000
    cross_validator: int = 80_000
    repairer: int = 40_000
    hard_cap: int = 100_000
    safety_factor: float = 0.85
    overlap_budget_ratio: float = 0.15
    default_overlap: int = 5
    min_overlap: int = 3


STAGE3_TOKEN_BUDGET = TokenBudgetConfig()
