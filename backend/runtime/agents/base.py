import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Type, TypeVar

from pydantic import BaseModel, ConfigDict

from core.llm import LLMClient
from core.models import PhaseType
from runtime.agents.models import AgentResult, EventMeta, EventContext, L0Summary, L1Summary
from runtime.agents.delta_state import DeltaStateManager
from runtime.game_logger import glog
import config

T = TypeVar("T", bound=BaseModel)


class BaseLLMCaller(ABC):

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

    @property
    def model_name(self) -> str:
        return self._config.model

    @property
    def thinking_budget(self) -> int:
        return self._config.thinking_budget

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
        module = sys.modules[type(self).__module__]
        prompt_path = Path(module.__file__).parent / self.prompt_file
        return prompt_path.read_text(encoding="utf-8")

    def build_prompt(self, template: str, **kwargs) -> str:
        return template

    def call_llm(self, prompt: str, *, model_override: str | None = None) -> T:
        return self.llm.generate_structured(
            prompt=prompt,
            response_model=self.response_model,
            model=model_override or self.model_name,
            temperature=self.temperature,
            thinking_budget=self.thinking_budget,
            extra_params=self.extra_params or None,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
        )

    def call_llm_text(self, prompt: str, *, model_override: str | None = None, _log: bool = True) -> str:
        return self.llm.generate(
            prompt=prompt,
            model=model_override or self.model_name,
            temperature=self.temperature,
            thinking_budget=self.thinking_budget,
            extra_params=self.extra_params or None,
            api_base=self.api_base,
            api_key_env=self.api_key_env,
            log=_log,
        )

    def call_llm_text_stream(
        self,
        prompt: str,
        on_chunk: Callable[[str], None],
        *,
        model_override: str | None = None,
    ) -> str:
        has_sent = False
        try:
            full_text = ""
            for chunk in self.llm.generate_stream(
                prompt=prompt,
                model=model_override or self.model_name,
                temperature=self.temperature,
                thinking_budget=self.thinking_budget,
                extra_params=self.extra_params or None,
                api_base=self.api_base,
                api_key_env=self.api_key_env,
            ):
                full_text += chunk
                has_sent = True
                on_chunk(chunk)
            return full_text
        except Exception:
            if has_sent:
                raise
            text = self.call_llm_text(prompt, model_override=model_override, _log=False)
            on_chunk(text)
            return text

    def log_generation(
        self,
        writer_type: str,
        input_data: BaseModel,
        output_text: str,
        prompt: str | None = None,
    ) -> None:
        log_data = {
            "writer_type": writer_type,
            "model": self.model_name,
            "thinking_budget": self.thinking_budget,
            "temperature": self.temperature,
            "extra_params": self.extra_params,
            "input": input_data.model_dump(),
            "output": output_text,
        }
        if prompt:
            log_data["prompt"] = prompt
        glog.log("WRITER", log_data)


class AgentContext(BaseModel):

    model_config = ConfigDict(frozen=True)

    event_meta: EventMeta
    event_context: EventContext
    phase: PhaseType
    phase_source: str
    phase_source_decision: str
    player_input: str | None = None
    previous_event: str | None = None


class GameState:

    __slots__ = ("delta_state", "l0_summaries", "l1_summaries", "current_event_id")

    def __init__(
        self,
        delta_state: DeltaStateManager,
        l0_summaries: list[L0Summary],
        l1_summaries: list[L1Summary],
        current_event_id: str,
    ):
        self.delta_state = delta_state
        self.l0_summaries = l0_summaries
        self.l1_summaries = l1_summaries
        self.current_event_id = current_event_id


class BaseAgent(ABC):

    _agent_executor: "AgentExecutor | None" = None

    def bind(self, executor: "AgentExecutor") -> None:
        self._agent_executor = executor

    def execute(
        self,
        context: AgentContext,
        state: GameState,
        **kwargs,
    ) -> AgentResult:
        raise NotImplementedError(f"{self.__class__.__name__}.execute() not implemented")


class AgentExecutor:

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, name: str, agent: BaseAgent) -> None:
        self._agents[name] = agent
        agent.bind(self)

    def get(self, name: str) -> BaseAgent:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered")
        return self._agents[name]

    def execute(
        self,
        name: str,
        context: AgentContext,
        state: GameState,
        **kwargs,
    ) -> AgentResult:
        return self.get(name).execute(context, state, **kwargs)
