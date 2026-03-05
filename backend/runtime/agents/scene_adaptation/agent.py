from core.llm import LLMClient
from runtime.agents.base import BaseAgent, AgentContext, GameState
from runtime.agents.scene_adaptation.bridge_planner import BridgePlanner
from runtime.agents.scene_adaptation.scene_adapter import SceneAdapter
from runtime.agents.models import BridgeResult, AdaptationPlan
from runtime.agents.delta_state import DeltaEntry


class SceneAdaptationAgent(BaseAgent):

    def __init__(self, llm: LLMClient):
        self._bridge_planner = BridgePlanner(llm)
        self._scene_adapter = SceneAdapter(llm)

    def execute(
        self,
        context: AgentContext,
        state: GameState,
        **kwargs,
    ) -> BridgeResult:
        premise_conflicts = kwargs["premise_conflicts"]
        active_deltas = state.delta_state.get_active_deltas()
        return self._bridge_planner.plan(
            premise_conflicts=premise_conflicts,
            active_deltas=active_deltas,
            previous_event=context.previous_event or "",
            next_phase_source=context.phase_source,
            preconditions=context.event_meta.preconditions,
        )

    def adapt_scene(
        self,
        event_id: str,
        event_original_text: str,
        active_deltas: list[DeltaEntry],
        archived_overrides_text: str = "",
    ) -> AdaptationPlan:
        return self._scene_adapter.adapt(
            event_id=event_id,
            event_original_text=event_original_text,
            active_deltas=active_deltas,
            archived_overrides_text=archived_overrides_text,
        )
