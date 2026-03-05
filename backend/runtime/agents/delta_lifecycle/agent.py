from runtime.agents.models import AgentResult
from runtime.agents.base import BaseAgent, GameState, AgentContext
from runtime.game_logger import glog


class DeltaContextResult(AgentResult):

    active_tags: str = ""
    already_activated: str = ""
    pending_echo_tags: str = ""
    archived_text: str = ""


class DeltaLifecycleAgent(BaseAgent):

    def execute(
        self,
        context: AgentContext,
        state: GameState,
        **kwargs,
    ) -> DeltaContextResult:
        ds = state.delta_state
        archived_text = ds.format_archived_text()
        return DeltaContextResult(
            active_tags=ds.format_active_tags(),
            already_activated=", ".join(ds.event_activated_deltas),
            pending_echo_tags=ds.format_pending_echo_tags(),
            archived_text=archived_text,
        )

    def create_delta(
        self,
        state: GameState,
        fact: str,
        source_event: str,
        intensity: int = 3,
    ) -> None:
        state.delta_state.create_delta(
            fact=fact,
            source_event=source_event,
            intensity=intensity,
        )
        glog.log("DELTA", {
            "action": "create",
            "fact": fact,
            "source_event": source_event,
            "intensity": intensity,
        })

    def complete_echoes(
        self,
        state: GameState,
        echo_ids: list[str],
    ) -> None:
        for echo_id in echo_ids:
            state.delta_state.complete_echo(echo_id)
        if echo_ids:
            glog.log("DELTA", {"action": "complete_echoes", "echo_ids": echo_ids})

    def process_activations(
        self,
        state: GameState,
        delta_ids: list[str],
        event_id: str,
    ) -> None:
        for did in delta_ids:
            state.delta_state.mark_activated(did, event_id)

    def generate_echo_instructions(
        self,
        state: GameState,
        compatible_ids: list[str],
    ) -> str:
        return state.delta_state.format_echo_instructions_tags(compatible_ids)

    def evolve_delta(
        self,
        state: GameState,
        delta_id: str,
        new_fact: str,
        new_intensity: int,
    ) -> None:
        state.delta_state.evolve_delta(delta_id, new_fact, new_intensity)
        glog.log("DELTA", {
            "action": "evolve",
            "delta_id": delta_id,
            "new_fact": new_fact,
            "new_intensity": new_intensity,
        })

    def event_boundary_maintenance(
        self,
        state: GameState,
        event_id: str,
    ) -> None:
        ds = state.delta_state
        ds.decay_event_activations(event_id)
        ds.tick_echo_timeouts()
        ds.reset_event_activations()
        glog.log("DELTA", {
            "action": "event_boundary_maintenance",
            "event_id": event_id,
            "active_count": len(ds.delta_entries),
            "archived_count": len(ds.archived_deltas),
        })
