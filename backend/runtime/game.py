import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.llm import LLMClient
from core.models import Event, PhaseType
from runtime.world import WorldPkgLoader
from runtime.agents.narrative_generation.writers.writer import UnifiedWriter
from runtime.agents.models import (
    EventContext,
    EventMeta,
    HistoryEntry,
    L0Summary,
    L1Summary,
    BridgeResult,
    DeviationAnalysis,
)
from runtime.agents.memory_compression.l0_compressor import L0Compressor
from runtime.agents.memory_compression.l1_compressor import L1Compressor
from runtime.agents.context_enrichment.history_recall import HistoryRecaller
from runtime.agents.context_enrichment.entity_recognizer import EntityRecognizerAgent
from runtime.agents.deviation_guidance.deviation_controller import DeviationController
from runtime.tools.lorebook_query import LorebookQuery
from runtime.agents.delta_state import DeltaStateManager
from runtime.agents.base import AgentExecutor, GameState, AgentContext
from runtime.agents.memory_compression import MemoryCompressionAgent
from runtime.agents.delta_lifecycle import DeltaLifecycleAgent
from runtime.agents.context_enrichment import ContextEnrichmentAgent
from runtime.agents.deviation_guidance import DeviationGuidanceAgent
from runtime.agents.narrative_generation import (
    NarrativeGenerationAgent,
    NarrativeGenerationResult,
)
from runtime.agents.scene_adaptation import SceneAdaptationAgent
import config
from runtime.game_logger import glog


@dataclass
class _PrefetchSlot:
    action: str                                                  
    future: Future | None = None
    result: str | None = None
    completed: threading.Event = field(default_factory=threading.Event)
    error: Exception | None = None
    generation_result: NarrativeGenerationResult | None = None
    event: Event | None = None
    phase: PhaseType | None = None
    game_ending: bool = False
    chunk_queue: queue.Queue = field(default_factory=queue.Queue)
    bridge_data: BridgeResult | None = None


@dataclass
class ResponseState:
    phase: str | None
    event_id: str | None
    turn: int
    awaiting_next_event: bool
    game_ended: bool = False


_REQUIRED_SAVE_KEYS = {
    "current_event_id", "current_phase", "total_turns",
    "player_name", "awaiting_next_event", "event_context",
    "l0_summaries", "l1_summaries", "_l1_counter",
    "game_ended", "delta_state",
}


def _validate_save_data(data: dict) -> str | None:
    missing = _REQUIRED_SAVE_KEYS - data.keys()
    if missing:
        return f"缺少必要字段：{missing}"
    if not isinstance(data.get("total_turns"), int):
        return "字段 total_turns 类型错误"
    if data.get("current_phase") not in ("setup", "confrontation", "resolution"):
        return f"字段 current_phase 值无效：{data.get('current_phase')}"
    return None


class GameEngine:

    def __init__(self, worldpkg_path: Path, saves_dir: Path | None = None):
        self._lock = threading.RLock()

        self.world = WorldPkgLoader(worldpkg_path)
        self.llm = LLMClient()
        self.delta_state = DeltaStateManager()

        protagonist = self.world.get_protagonist()
        protagonist_name = protagonist.name if protagonist else ""
        protagonist_aliases = protagonist.aliases if protagonist else []

        writer = UnifiedWriter(
            llm_client=self.llm,
            protagonist_name=protagonist_name,
            protagonist_aliases=protagonist_aliases,
        )

        lorebook_dir = worldpkg_path / "lorebook"
        lorebook_query = LorebookQuery(lorebook_dir)
        lorebook_content = lorebook_query.to_lorebook_content()

        self.current_event_id: str | None = None
        self.current_phase: PhaseType = PhaseType.SETUP
        self.total_turns: int = 0
        self.player_name: str = ""
        self.awaiting_next_event: bool = False
        self.event_context: EventContext = EventContext()
        self.l0_summaries: list[L0Summary] = []
        self.l1_summaries: list[L1Summary] = []
        self.previous_event_content: str | None = None
        self._reentry_pending: bool = False
        self._current_adaptation_plan: list[dict] | None = None
        self.game_ended: bool = False
        self._last_maintained_event_id: str | None = None
        self.on_narrative_chunk = None

        self._prefetch_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="prefetch")
        self._prefetch_slot: _PrefetchSlot | None = None
        self.response_state = ResponseState(
            phase=None, event_id=None, turn=0,
            awaiting_next_event=False, game_ended=False,
        )

        self.agents = AgentExecutor()
        self.agents.register("memory_compression", MemoryCompressionAgent(
            l0_compressor=L0Compressor(self.llm, protagonist_name=protagonist_name),
            l1_compressor=L1Compressor(self.llm, protagonist_name=protagonist_name),
        ))
        self.agents.register("delta_lifecycle", DeltaLifecycleAgent())
        self.agents.register("context_enrichment", ContextEnrichmentAgent(
            history_agent=HistoryRecaller(self.llm),
            entity_agent=EntityRecognizerAgent(self.llm),
            lorebook_query=lorebook_query,
            lorebook_content=lorebook_content,
        ))
        self.agents.register("deviation_guidance", DeviationGuidanceAgent(
            deviation_controller=DeviationController(self.llm),
        ))
        self.agents.register("narrative_generation", NarrativeGenerationAgent(
            llm=self.llm,
            writer=writer,
        ))
        self.agents.register("scene_adaptation", SceneAdaptationAgent(
            llm=self.llm,
        ))

    def new_game(self, on_chunk=None) -> str:
        with self._lock:
            glog.start_session("new_game")

            protagonist = self.world.get_protagonist()
            if not protagonist:
                raise ValueError("WorldPkg 中没有找到主角（importance=protagonist）")

            self.player_name = protagonist.name

            first_event = self.world.get_first_event()
            if not first_event:
                raise ValueError("WorldPkg 中没有找到事件")

            self.current_event_id = first_event.id
            self.current_phase = PhaseType.SETUP
            self.total_turns = 0
            self.awaiting_next_event = False

            self.event_context = EventContext()

            self.l0_summaries = []
            self.l1_summaries = []
            self.agents.get("memory_compression").l1_counter = 0
            self.previous_event_content = None

            self.delta_state = DeltaStateManager()
            self._reentry_pending = False
            self._current_adaptation_plan = None
            self._last_maintained_event_id = None

            self._clear_auto_save()

            glog.log("GAME_STATE", {
                "action": "new_game",
                "player": self.player_name,
                "first_event": first_event.id,
            })

            self._invalidate_prefetch()

            saved_cb = self.on_narrative_chunk
            if on_chunk:
                self.on_narrative_chunk = on_chunk

            try:
                response = self._generate_phase_narrative(first_event, PhaseType.SETUP)
            finally:
                self.on_narrative_chunk = saved_cb

            if first_event.type == "narrative" and not self._reentry_pending:
                self.awaiting_next_event = True

            self._try_auto_save("new_game")

            self._capture_response_state()
            self._maybe_schedule_prefetch()
            return response

    def load_game(self, slot: int) -> str:
        with self._lock:
            glog.start_session(f"load_{slot}")
            glog.log("GAME_STATE", {"action": "load_game", "slot": slot})

            save_dir = config.SAVES_DIR / f"save_{slot:03d}"
            if not save_dir.exists():
                return f"[错误] 槽位 {slot} 没有存档"

            state_path = save_dir / "state.json"
            if not state_path.exists():
                return f"[错误] 存档 {slot} 数据损坏（缺少 state.json）"

            metadata_path = save_dir / "metadata.json"
            if metadata_path.exists():
                meta = json.loads(metadata_path.read_text(encoding="utf-8"))
                saved_title = meta.get("worldpkg_title", "")
                if saved_title and saved_title != self.world.metadata.title:
                    return (
                        f"[错误] 存档与当前作品不匹配：\n"
                        f"  存档来自「{saved_title}」，当前加载「{self.world.metadata.title}」"
                    )

            data = json.loads(state_path.read_text(encoding="utf-8"))

            error = _validate_save_data(data)
            if error:
                return f"[错误] 存档 {slot} 数据损坏：{error}"

            self._invalidate_prefetch()
            try:
                self._restore_save_state(data)
            except Exception as e:
                return f"[错误] 存档 {slot} 恢复失败：{e}"

            self._try_auto_save("load_game")

            self._capture_response_state()
            return self._build_resume_text()

    def _restore_save_state(self, data: dict) -> None:
        self.current_event_id = data["current_event_id"]
        self.current_phase = PhaseType(data["current_phase"])
        self.total_turns = data["total_turns"]
        self.player_name = data["player_name"]
        self.awaiting_next_event = data["awaiting_next_event"]
        self.event_context = EventContext.model_validate(data["event_context"])
        self.l0_summaries = [L0Summary.model_validate(s) for s in data["l0_summaries"]]
        self.l1_summaries = [L1Summary.model_validate(s) for s in data["l1_summaries"]]
        self.agents.get("memory_compression").restore_save_state({"l1_counter": data["_l1_counter"]})
        self.previous_event_content = data.get("previous_event_content")
        self._reentry_pending = data.get("_reentry_pending", False)
        self._current_adaptation_plan = data.get("_current_adaptation_plan")
        self.game_ended = data["game_ended"]
        self.delta_state = DeltaStateManager.from_dict(data["delta_state"])
        self._last_maintained_event_id = None

    def _build_resume_text(self) -> str:
        parts = []

        if self.event_context.setup_narrative:
            parts.append(self.event_context.setup_narrative)

        if self.event_context.confrontation_history:
            for entry in self.event_context.confrontation_history:
                parts.append(f"> {entry.player_input}")
                if entry.response_summary:
                    parts.append(entry.response_summary)

        if not parts:
            parts.append("（存档已加载）")

        return "\n\n".join(parts)

    def _try_auto_save(self, location: str) -> None:
        try:
            self.auto_save()
        except Exception as e:
            glog.log("AUTO_SAVE", {"error": str(e), "location": location})

    def process_input(self, player_input: str) -> str:
        with self._lock:
            glog.log("PLAYER", {
                "input": player_input,
                "event_id": self.current_event_id,
                "phase": self.current_phase.value if self.current_phase else None,
                "turn": self.total_turns,
            })

            if self.current_event_id is None:
                return "[错误] 游戏尚未开始"

            if player_input.startswith("/"):
                return self._handle_command(player_input)

            if self.current_phase != PhaseType.CONFRONTATION:
                return "[提示] 当前阶段请按 Enter 继续"

            if not player_input.strip():
                return "[提示] 请输入你的行动"

            current_event = self.world.get_event(self.current_event_id)
            if not current_event:
                return "[错误] 当前事件不存在"

            ctx = self._build_agent_context(current_event, PhaseType.CONFRONTATION, player_input)
            state = self._build_game_state()

            extra_kwargs: dict = {}
            if self.on_narrative_chunk:
                extra_kwargs["on_chunk"] = self.on_narrative_chunk
            if self._current_adaptation_plan:
                from runtime.agents.narrative_generation.agent import _render_adaptation_plan_tags
                extra_kwargs["adaptation_plan_text"] = _render_adaptation_plan_tags(
                    self._current_adaptation_plan,
                )
                extra_kwargs["adaptation_plan_raw"] = self._current_adaptation_plan

            try:
                result: NarrativeGenerationResult = self.agents.execute(
                    "narrative_generation", ctx, state, **extra_kwargs,
                )
            except Exception as e:
                return f"[错误] 叙事生成失败: {e}"

            self._record_deviation_history(player_input, result.deviation_analysis)
            self.total_turns += 1

            delta_agent = self.agents.get("delta_lifecycle")
            if result.delta_fact:
                delta_agent.create_delta(
                    state, result.delta_fact,
                    self.current_event_id,
                    result.delta_intensity or 3,
                )
            delta_agent.complete_echoes(state, result.echo_completed_ids)
            if result.adaptation_plan:
                self._current_adaptation_plan = result.adaptation_plan

            self._update_event_context_after_response(result, player_input)

            if result.phase_complete:
                response = self._complete_current_event()
                self._try_auto_save("process_input_phase_complete")
                self._capture_response_state()
                self._maybe_schedule_prefetch()
                return response

            self._try_auto_save("process_input")
            self._capture_response_state()
            return result.narrative

    def _prepare_generation(
        self,
        event: Event,
        phase: PhaseType,
        player_input: str | None = None,
    ) -> tuple[AgentContext, GameState, dict]:
        ctx = self._build_agent_context(event, phase, player_input)
        state = self._build_game_state()
        extra_kwargs: dict = {}
        if phase == PhaseType.SETUP:
            extra_kwargs["event_original_text"] = self._get_phase_text_decision(event.id, phase)
        elif self._current_adaptation_plan:
            from runtime.agents.narrative_generation.agent import _render_adaptation_plan_tags
            extra_kwargs["adaptation_plan_text"] = _render_adaptation_plan_tags(
                self._current_adaptation_plan,
            )
            extra_kwargs["adaptation_plan_raw"] = self._current_adaptation_plan
        return ctx, state, extra_kwargs

    def _finalize_generation(
        self,
        result: NarrativeGenerationResult,
        event: Event,
        phase: PhaseType,
    ) -> str:
        delta_agent = self.agents.get("delta_lifecycle")
        delta_agent.complete_echoes(self._build_game_state(), result.echo_completed_ids)

        if phase == PhaseType.SETUP:
            self.event_context.setup_narrative = result.narrative
            self._current_adaptation_plan = result.adaptation_plan
        elif phase == PhaseType.CONFRONTATION:
            self.event_context.confrontation_history.append(
                HistoryEntry(player_input=None, response_summary=result.narrative)
            )
            if result.adaptation_plan:
                self._current_adaptation_plan = result.adaptation_plan

        return result.narrative

    def _generate_phase_narrative(
        self,
        event: Event,
        phase: PhaseType,
        player_input: str | None = None,
    ) -> str:
        ctx, state, extra_kwargs = self._prepare_generation(event, phase, player_input)

        if self.on_narrative_chunk:
            extra_kwargs["on_chunk"] = self.on_narrative_chunk

        result: NarrativeGenerationResult = self.agents.execute(
            "narrative_generation", ctx, state, **extra_kwargs,
        )

        is_event_entry = (
            self.event_context.setup_narrative is None
            and not self.event_context.confrontation_history
        )
        if result.premise_conflicts and is_event_entry:
            return self._handle_structural_conflict(
                event, ctx, state, result.premise_conflicts,
            )

        return self._finalize_generation(result, event, phase)

    def _handle_structural_conflict(
        self,
        event: Event,
        ctx: AgentContext,
        state: GameState,
        premise_conflicts: list[dict],
    ) -> str:
        valid_conflicts = [
            c for c in premise_conflicts
            if all(k in c for k in ("delta_id", "conflicting_premise", "conflict_reason"))
        ]
        if not valid_conflicts:
            raise RuntimeError(
                f"无有效 premise_conflicts（event={event.id}）: {premise_conflicts}"
            )

        bridge_result: BridgeResult = self.agents.execute(
            "scene_adaptation", ctx, state,
            premise_conflicts=valid_conflicts,
        )

        if not bridge_result.delta_evolutions:
            raise RuntimeError(
                f"BridgePlanner 返回空 delta_evolutions（event={event.id}）"
            )

        delta_agent = self.agents.get("delta_lifecycle")
        for evo in bridge_result.delta_evolutions:
            delta_agent.evolve_delta(
                state,
                delta_id=evo.original_delta_id,
                new_fact=evo.evolved_fact,
                new_intensity=evo.evolved_intensity,
            )

        self.event_context.setup_narrative = bridge_result.bridge_narrative
        self._reentry_pending = True

        glog.log("GAME_STATE", {
            "action": "structural_conflict_bridge",
            "event_id": event.id,
            "conflicts": len(valid_conflicts),
            "evolutions": len(bridge_result.delta_evolutions),
        })

        return bridge_result.bridge_narrative

    def _build_agent_context(
        self,
        event: Event,
        phase: PhaseType,
        player_input: str | None = None,
        *,
        event_context: EventContext | None = None,
    ) -> AgentContext:
        return AgentContext(
            event_meta=EventMeta(
                event_id=event.id,
                importance=event.importance.value if hasattr(event.importance, 'value') else str(event.importance),
                goal=event.goal,
                event_type=event.type,
                soft_guide_hints=event.soft_guide_hints,
                preconditions=[
                    p.model_dump(by_alias=True)
                    for p in self.world.get_preconditions(event.id)
                ],
            ),
            event_context=event_context if event_context is not None else self.event_context,
            phase=phase,
            phase_source=self._get_phase_text_full(event.id, phase),
            phase_source_decision=self._get_phase_text_decision(event.id, phase),
            player_input=player_input,
            previous_event=self.previous_event_content,
        )

    def _update_event_context_after_response(
        self,
        result: NarrativeGenerationResult,
        player_input: str,
    ) -> None:
        summary = result.narrative or "（冲突阶段结束，玩家做出最终决定）"
        self.event_context.confrontation_history.append(
            HistoryEntry(
                player_input=player_input,
                response_summary=summary,
            )
        )

    def _record_deviation_history(
        self,
        player_input: str,
        analysis: DeviationAnalysis | None,
    ) -> None:
        if analysis is None:
            return

        self.event_context.deviation_history.append(
            HistoryEntry(
                player_input=player_input,
                response_summary=json.dumps(analysis.model_dump(), ensure_ascii=False),
            )
        )

    def _pre_advance_from_setup(self) -> tuple[Event | None, PhaseType, str]:
        glog.log("GAME_STATE", {"action": "advance_from_setup", "event_id": self.current_event_id})

        if self.current_event_id is None:
            return None, PhaseType.SETUP, "error"

        if self._reentry_pending:
            self._reentry_pending = False
            self._save_current_event_as_previous()
            self.event_context = EventContext()
            current = self.world.get_event(self.current_event_id)
            return current, PhaseType.SETUP, "reentry"

        current_event = self.world.get_event(self.current_event_id)
        if not current_event:
            return None, PhaseType.SETUP, "error"

        if current_event.type == "narrative":
            event = self._pre_advance_to_next_event()
            if event is None:
                return None, PhaseType.SETUP, "game_ending"
            return event, PhaseType.SETUP, "chain_to_next_event"

        self.current_phase = PhaseType.CONFRONTATION
        return current_event, PhaseType.CONFRONTATION, "normal"

    def _post_advance_from_setup(self, event: Event, special: str) -> None:
        if special == "reentry":
            current = self.world.get_event(self.current_event_id)
            if current and current.type == "narrative":
                self.awaiting_next_event = True
        elif special == "chain_to_next_event":
            self._post_advance_to_next_event(event)
            return
        self._try_auto_save("_post_advance_from_setup")

    def _maintain_boundary_if_needed(self) -> None:
        if not self.current_event_id:
            return
        self._save_current_event_as_previous()
        if self.current_event_id != self._last_maintained_event_id:
            self.agents.get("delta_lifecycle").event_boundary_maintenance(
                self._build_game_state(), self.current_event_id,
            )
            self._last_maintained_event_id = self.current_event_id

    def advance_from_setup(self) -> str:
        with self._lock:
            event, phase, special = self._pre_advance_from_setup()

            if special == "error":
                return "[错误] 游戏尚未开始" if self.current_event_id is None else "[错误] 当前事件不存在"
            if special == "game_ending":
                return self._handle_game_ending()

            narrative = self._generate_phase_narrative(event, phase)
            self._post_advance_from_setup(event, special)
            return narrative

    def _pre_advance_to_next_event(self) -> Event | None:
        glog.log("GAME_STATE", {"action": "advance_to_next_event", "from_event": self.current_event_id})

        self._try_auto_save("_pre_advance_to_next_event")

        self.awaiting_next_event = False
        self._current_adaptation_plan = None

        self._maintain_boundary_if_needed()

        next_event_id = self.world.get_next_event_id(self.current_event_id)
        if not next_event_id:
            return None

        next_event = self.world.get_event(next_event_id)
        if not next_event:
            return None

        self.current_event_id = next_event_id
        self.event_context = EventContext()
        self.current_phase = PhaseType.SETUP
        return next_event

    def _post_advance_to_next_event(self, event: Event) -> None:
        if event.type == "narrative" and not self._reentry_pending:
            self.awaiting_next_event = True
        self._try_auto_save("_post_advance_to_next_event")

    def advance_to_next_event(self) -> str:
        with self._lock:
            event = self._pre_advance_to_next_event()
            if event is None:
                return self._handle_game_ending()

            narrative = self._generate_phase_narrative(event, PhaseType.SETUP)
            self._post_advance_to_next_event(event)
            return narrative

    def continue_game(self, on_chunk=None) -> str:
        with self._lock:
            slot = self._prefetch_slot

            if slot and slot.completed.is_set() and slot.error is None and slot.result is not None:
                self._prefetch_slot = None
                glog.log("PREFETCH", {"action": "cache_hit"})
                if on_chunk:
                    on_chunk(slot.result)
                self._apply_prefetch_state(slot)
                self._capture_response_state()
                self._maybe_schedule_prefetch()
                return slot.result

            if slot and not slot.completed.is_set():
                self._prefetch_slot = None
                glog.log("PREFETCH", {"action": "stream_takeover", "target": slot.action})
            else:
                slot = None
                self._invalidate_prefetch()

        if slot is not None:
            narrative, streamed = self._stream_from_prefetch(slot, on_chunk)
            if narrative is not None:
                if not streamed and on_chunk:
                    on_chunk(narrative)
                with self._lock:
                    self._apply_prefetch_state(slot)
                    self._capture_response_state()
                    self._maybe_schedule_prefetch()
                return narrative
            if streamed:
                raise slot.error or RuntimeError("Prefetch 流式传输中断")

        with self._lock:
            self._invalidate_prefetch()
            saved_cb = self.on_narrative_chunk
            self.on_narrative_chunk = on_chunk
            try:
                if self.awaiting_next_event:
                    result = self.advance_to_next_event()
                elif self.current_phase == PhaseType.SETUP:
                    result = self.advance_from_setup()
                else:
                    result = "[提示] 当前阶段无法自动推进，请输入行动"
            finally:
                self.on_narrative_chunk = saved_cb
            self._capture_response_state()
            self._maybe_schedule_prefetch()
            return result

    def _maybe_schedule_prefetch(self) -> None:
        if self._prefetch_slot is not None:
            return
        if self.game_ended or self._reentry_pending:
            return

        action = None
        if self.awaiting_next_event:
            action = "advance_to_next_event"
        elif self.current_phase == PhaseType.SETUP:
            current = self.world.get_event(self.current_event_id)
            if current and current.type == "interactive":
                action = "advance_from_setup"

        if action:
            slot = _PrefetchSlot(action=action)
            self._prefetch_slot = slot
            slot.future = self._prefetch_pool.submit(self._run_prefetch, slot)
            glog.log("PREFETCH", {"action": "scheduled", "target": action})

    def _run_prefetch(self, slot: _PrefetchSlot) -> None:
        try:
            with self._lock:
                if self._prefetch_slot is not slot:
                    return

                if slot.action == "advance_to_next_event":
                    self._maintain_boundary_if_needed()

                    next_id = self.world.get_next_event_id(self.current_event_id)
                    if not next_id:
                        slot.result = f"\n\n《{self.world.metadata.title}》的故事到此结束。\n"
                        slot.game_ending = True
                        return
                    next_event = self.world.get_event(next_id)
                    if not next_event:
                        return

                    slot.event = next_event
                    slot.phase = PhaseType.SETUP
                    ctx = self._build_agent_context(
                        next_event, PhaseType.SETUP, event_context=EventContext(),
                    )
                    state = GameState(
                        delta_state=self.delta_state,
                        l0_summaries=self.l0_summaries,
                        l1_summaries=self.l1_summaries,
                        current_event_id=next_id,
                    )
                    extra_kwargs: dict = {
                        "event_original_text": self._get_phase_text_decision(next_id, PhaseType.SETUP),
                    }
                    extra_kwargs["on_chunk"] = lambda chunk: slot.chunk_queue.put(chunk)

                elif slot.action == "advance_from_setup":
                    event = self.world.get_event(self.current_event_id)
                    if not event:
                        return
                    slot.event = event
                    slot.phase = PhaseType.CONFRONTATION
                    ctx, state, extra_kwargs = self._prepare_generation(
                        event, PhaseType.CONFRONTATION,
                    )
                    extra_kwargs["on_chunk"] = lambda chunk: slot.chunk_queue.put(chunk)

                else:
                    return

            result: NarrativeGenerationResult = self.agents.execute(
                "narrative_generation", ctx, state, **extra_kwargs,
            )

            if result.premise_conflicts:
                bridge_result = self._prefetch_bridge(
                    slot, ctx, state, result.premise_conflicts,
                )
                if bridge_result is not None:
                    slot.bridge_data = bridge_result
                    slot.result = bridge_result.bridge_narrative
                    slot.chunk_queue.put(bridge_result.bridge_narrative)
                    glog.log("PREFETCH", {"action": "bridge_completed", "target": slot.action})
                else:
                    glog.log("PREFETCH", {"action": "bridge_failed", "target": slot.action})
            else:
                slot.generation_result = result
                slot.result = result.narrative
                glog.log("PREFETCH", {"action": "completed", "target": slot.action})

        except Exception as e:
            slot.error = e
            glog.log("PREFETCH", {
                "action": "error", "target": slot.action, "error": str(e),
            })
        finally:
            slot.chunk_queue.put(None)
            slot.completed.set()

    def _prefetch_bridge(
        self,
        slot: _PrefetchSlot,
        ctx: AgentContext,
        state: GameState,
        premise_conflicts: list[dict],
    ) -> BridgeResult | None:
        valid_conflicts = [
            c for c in premise_conflicts
            if all(k in c for k in ("delta_id", "conflicting_premise", "conflict_reason"))
        ]
        if not valid_conflicts:
            return None

        try:
            bridge_result: BridgeResult = self.agents.execute(
                "scene_adaptation", ctx, state,
                premise_conflicts=valid_conflicts,
            )
            if not bridge_result.delta_evolutions:
                return None
            return bridge_result
        except Exception as e:
            glog.log("PREFETCH", {"action": "bridge_planner_error", "error": str(e)})
            return None

    def _stream_from_prefetch(
        self, slot: _PrefetchSlot, on_chunk,
    ) -> tuple[str | None, bool]:
        chunks: list[str] = []
        while True:
            try:
                chunk = slot.chunk_queue.get(timeout=180)
            except queue.Empty:
                slot.error = TimeoutError("Prefetch 流式输出超时")
                break
            if chunk is None:
                break
            chunks.append(chunk)
            if on_chunk:
                on_chunk(chunk)

        slot.completed.wait(timeout=60)

        if slot.error is not None or slot.result is None:
            return None, len(chunks) > 0
        return slot.result, len(chunks) > 0

    def _apply_prefetch_state(self, slot: _PrefetchSlot) -> None:
        if slot.game_ending:
            self.flush_compressions()
            self.game_ended = True
            return

        if slot.bridge_data is not None:
            self.awaiting_next_event = False
            self._current_adaptation_plan = None
            self.current_event_id = slot.event.id
            self.event_context = EventContext()
            self.current_phase = PhaseType.SETUP

            delta_agent = self.agents.get("delta_lifecycle")
            game_state = self._build_game_state()
            for evo in slot.bridge_data.delta_evolutions:
                delta_agent.evolve_delta(
                    game_state,
                    delta_id=evo.original_delta_id,
                    new_fact=evo.evolved_fact,
                    new_intensity=evo.evolved_intensity,
                )
            self.event_context.setup_narrative = slot.bridge_data.bridge_narrative
            self._reentry_pending = True

            glog.log("GAME_STATE", {
                "action": "structural_conflict_bridge",
                "event_id": slot.event.id,
                "evolutions": len(slot.bridge_data.delta_evolutions),
            })
            self._try_auto_save("prefetch_bridge")
            return

        if slot.action == "advance_to_next_event":
            self.awaiting_next_event = False
            self._current_adaptation_plan = None
            self.current_event_id = slot.event.id
            self.event_context = EventContext()
            self.current_phase = PhaseType.SETUP
        elif slot.action == "advance_from_setup":
            self.current_phase = PhaseType.CONFRONTATION

        self._finalize_generation(slot.generation_result, slot.event, slot.phase)

        if slot.action == "advance_to_next_event":
            self._post_advance_to_next_event(slot.event)
        elif slot.action == "advance_from_setup":
            self._try_auto_save("prefetch_result")

    def _invalidate_prefetch(self) -> None:
        if self._prefetch_slot:
            glog.log("PREFETCH", {"action": "invalidated"})
        self._prefetch_slot = None

    def _capture_response_state(self) -> None:
        self.response_state = ResponseState(
            phase=self.current_phase.value if self.current_phase else None,
            event_id=self.current_event_id,
            turn=self.total_turns,
            awaiting_next_event=self.awaiting_next_event,
            game_ended=self.game_ended,
        )

    def _save_current_event_as_previous(self) -> None:
        if self.current_event_id and any(
            s.event_id == self.current_event_id for s in self.l0_summaries
        ):
            existing = next(s for s in self.l0_summaries if s.event_id == self.current_event_id)
            self.previous_event_content = existing.summary
            return

        parts = []

        if self.event_context.setup_narrative:
            parts.append(self.event_context.setup_narrative)

        for entry in self.event_context.confrontation_history:
            parts.append(f"[玩家] {entry.player_input}")
            if entry.response_summary:
                parts.append(f"[系统] {entry.response_summary}")

        event_text = "\n\n".join(parts) if parts else None
        if not event_text or not self.current_event_id:
            self.previous_event_content = None
            return
        l0 = self.agents.get("memory_compression").compress_event_sync_l0(
            self._build_game_state(), self.current_event_id, event_text,
        )
        self.previous_event_content = l0.summary

    def _build_game_state(self) -> GameState:
        return GameState(
            delta_state=self.delta_state,
            l0_summaries=self.l0_summaries,
            l1_summaries=self.l1_summaries,
            current_event_id=self.current_event_id or "",
        )

    def _get_phase_text(self, event_id: str, phase_type: PhaseType, *, full: bool) -> str:
        event = self.world.get_event(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")
        if event.type == "narrative":
            return self.world.get_event_text_full(event_id) if full else self.world.get_event_text_decision(event_id)
        return self.world.get_phase_text_full(event_id, phase_type.value) if full else self.world.get_phase_text_decision(event_id, phase_type.value)

    def _get_phase_text_full(self, event_id: str, phase_type: PhaseType) -> str:
        return self._get_phase_text(event_id, phase_type, full=True)

    def _get_phase_text_decision(self, event_id: str, phase_type: PhaseType) -> str:
        return self._get_phase_text(event_id, phase_type, full=False)

    def _complete_current_event(self) -> str:
        if self.current_event_id is None:
            return ""

        current_event = self.world.get_event(self.current_event_id)
        if not current_event:
            return ""

        self.current_phase = PhaseType.RESOLUTION
        self.awaiting_next_event = True
        return self._generate_phase_narrative(current_event, PhaseType.RESOLUTION)

    def _handle_game_ending(self) -> str:
        self.flush_compressions()
        self.game_ended = True
        return f"\n\n《{self.world.metadata.title}》的故事到此结束。\n"

    def flush_compressions(self) -> None:
        self.agents.get("memory_compression").flush()

    def _collect_save_state(self) -> dict:
        l0_snapshot = list(self.l0_summaries)
        l1_snapshot = list(self.l1_summaries)
        return {
            "current_event_id": self.current_event_id,
            "current_phase": self.current_phase.value,
            "total_turns": self.total_turns,
            "player_name": self.player_name,
            "awaiting_next_event": self.awaiting_next_event,
            "event_context": self.event_context.model_dump(),
            "l0_summaries": [s.model_dump() for s in l0_snapshot],
            "l1_summaries": [s.model_dump() for s in l1_snapshot],
            "_l1_counter": self.agents.get("memory_compression").get_save_state()["l1_counter"],
            "previous_event_content": self.previous_event_content,
            "delta_state": self.delta_state.to_dict(),
            "_reentry_pending": self._reentry_pending,
            "_current_adaptation_plan": self._current_adaptation_plan,
            "game_ended": self.game_ended,
        }

    def save_game(self, slot: int, description: str = "") -> str:
        with self._lock:
            self.flush_compressions()

            if not description:
                event = self.world.get_event(self.current_event_id) if self.current_event_id else None
                if not event:
                    event_summary = "未知"
                elif event.type == "narrative":
                    event_summary = event.decision_text[:50]
                else:
                    phase = self.world.get_phase(event.id, self.current_phase.value)
                    event_summary = phase.decision_text[:50] if phase and phase.decision_text else event.goal[:50]
                description = f"{event_summary} - {self.current_phase.value} - 轮次{self.total_turns}"

            save_dir = config.SAVES_DIR / f"save_{slot:03d}"
            self._write_save(save_dir, description)
            return f"游戏已保存到槽位 {slot}"

    def auto_save(self) -> None:
        save_dir = config.SAVES_DIR / "save_000"
        self._write_save(save_dir, "自动存档")

    def _write_save(self, save_dir: Path, description: str) -> None:
        save_dir.mkdir(parents=True, exist_ok=True)

        state_data = self._collect_save_state()
        (save_dir / "state.json").write_text(
            json.dumps(state_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        metadata = {
            "save_time": datetime.now().isoformat(),
            "player_name": self.player_name,
            "current_event_id": self.current_event_id,
            "current_phase": self.current_phase.value,
            "total_turns": self.total_turns,
            "description": description,
            "worldpkg_title": self.world.metadata.title,
        }
        (save_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_saves(self) -> list[dict]:
        saves = []
        if not config.SAVES_DIR.exists():
            return saves
        for save_dir in sorted(config.SAVES_DIR.iterdir()):
            if save_dir.is_dir() and save_dir.name.startswith("save_"):
                metadata_path = save_dir / "metadata.json"
                if metadata_path.exists():
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    slot = int(save_dir.name.split("_")[1])
                    saves.append({"slot": slot, **metadata})
        return saves

    def _clear_auto_save(self) -> None:
        import shutil
        save_dir = config.SAVES_DIR / "save_000"
        if save_dir.exists():
            shutil.rmtree(save_dir)

    def shutdown(self) -> None:
        self._invalidate_prefetch()
        self._prefetch_pool.shutdown(wait=False)
        self.agents.get("memory_compression").shutdown()
        glog.log("GAME_STATE", {
            "action": "shutdown",
            "l0_count": len(self.l0_summaries),
            "l1_count": len(self.l1_summaries),
        })
        glog.end_session()

    def _handle_command(self, command: str) -> str:
        cmd = command.lower().strip()

        if cmd in ("/help", "/h"):
            return (
                "【可用命令】\n"
                "/save [槽位] - 保存游戏（默认槽位1）\n"
                "/saves - 列出所有存档\n"
                "/status - 查看当前状态\n"
                "/restart - 重新开始游戏\n"
                "/quit - 退出游戏"
            )

        if cmd.startswith("/save") and not cmd.startswith("/saves"):
            parts = cmd.split()
            slot = int(parts[1]) if len(parts) > 1 else 1
            return self.save_game(slot)

        if cmd == "/saves":
            saves = self.list_saves()
            if not saves:
                return "没有找到存档"
            lines = ["【存档列表】"]
            for save in saves:
                lines.append(
                    f"  [{save['slot']}] {save['description']} - {save['save_time'][:19]}"
                )
            return "\n".join(lines)

        if cmd == "/status":
            return (
                f"【当前状态】\n"
                f"玩家：{self.player_name}\n"
                f"当前事件：{self.current_event_id}\n"
                f"当前阶段：{self.current_phase.value}\n"
                f"轮次：{self.total_turns}"
            )

        if cmd == "/restart":
            return self.new_game()

        return f"未知命令：{command}\n输入 /help 查看可用命令"
