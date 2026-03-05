from pathlib import Path
import threading

from core.llm import LLMClient
from core.models import PhaseType
from runtime.agents.models import AgentResult, ToolCall, ToolResult, DeviationAnalysis
from runtime.agents.base import BaseAgent, GameState, AgentContext
from runtime.agents.narrative_generation.orchestrator import (
    PHASE_CONFIGS,
    LoopConfig,
    run_tool_loop,
)
from runtime.agents.narrative_generation.orchestrator import load_sections
from runtime.agents.narrative_generation.writer_bridge import (
    build_orchestrator_input,
    format_confrontation_history,
)
from runtime.agents.narrative_generation.writers.writer import WriterInput
import config
from runtime.game_logger import glog

from pydantic import Field


class NarrativeGenerationResult(AgentResult):

    narrative: str = ""
    awaiting_input: bool = False
    phase_complete: bool = False
    delta_fact: str | None = None
    delta_intensity: int | None = None
    activated_delta_ids: list[str] = Field(default_factory=list)
    echo_completed_ids: list[str] = Field(default_factory=list)
    premise_conflicts: list[dict] = Field(default_factory=list)
    adaptation_plan: list[dict] | None = None
    deviation_analysis: DeviationAnalysis | None = None


class NarrativeGenerationAgent(BaseAgent):

    def __init__(self, llm: LLMClient, writer: object):
        self._llm = llm
        self._writer = writer

        self._phase_prompts: dict[PhaseType, tuple[str, str]] = {}
        self._loop_configs: dict[PhaseType, LoopConfig] = {}

        shared = load_sections(_PROMPTS_DIR / "orchestrator_shared.txt")
        for phase, pc in PHASE_CONFIGS.items():
            raw_system = _load_prompt(pc.system_prompt_file)
            system_prompt = (
                raw_system
                .replace("{shared_tools}", shared["shared_tools"])
                .replace("{shared_principles}", shared["shared_principles"])
                .replace("{shared_output_format}", shared["shared_output_format"])
                .replace("{shared_writing_guidance}", shared["shared_writing_guidance"])
            )
            assert "{shared_" not in system_prompt, f"{phase}: unresolved placeholder"
            input_template = _load_prompt(pc.input_template_file)
            self._phase_prompts[phase] = (system_prompt, input_template)

            llm_cfg = config.get_llm_config(pc.config_name)
            self._loop_configs[phase] = LoopConfig(
                model=llm_cfg.model,
                temperature=llm_cfg.temperature,
                thinking_budget=llm_cfg.thinking_budget,
                config_name=pc.config_name,
                extra_params=llm_cfg.extra_params,
                api_base=llm_cfg.api_base,
                api_key_env=llm_cfg.api_key_env,
            )

    def execute(
        self,
        context: AgentContext,
        state: GameState,
        **kwargs,
    ) -> NarrativeGenerationResult:
        phase = context.phase

        delta_ctx = self._agent_executor.get("delta_lifecycle").execute(context, state)

        system_prompt, input_template = self._phase_prompts[phase]
        history_text = format_confrontation_history(
            context.event_context.confrontation_history,
        )
        user_input = build_orchestrator_input(
            input_template, context, delta_ctx, history_text,
        )

        captured: dict = {
            "delta_ctx": delta_ctx,
            "event_original_text": kwargs.get("event_original_text", context.phase_source_decision),
        }
        captured_lock = threading.Lock()

        def tool_handler(tc: ToolCall) -> ToolResult:
            return self._handle_tool_call(tc, context, state, captured, captured_lock)

        loop_result = run_tool_loop(
            self._llm, system_prompt, user_input,
            self._loop_configs[phase], tool_handler,
        )

        deviation_analysis = captured.get("deviation_analysis")

        if "request_bridge" in loop_result.tool_results:
            return NarrativeGenerationResult(
                premise_conflicts=captured.get("bridge_conflicts", []),
                deviation_analysis=deviation_analysis,
            )

        adaptation_plan_raw = captured.get("adaptation_plan_raw") or kwargs.get("adaptation_plan_raw")

        delta_agent = self._agent_executor.get("delta_lifecycle")
        activated_ids = loop_result.orchestrator_meta.get("activated_deltas", [])
        echo_compatible = loop_result.orchestrator_meta.get("echo_compatible", [])

        delta_agent.process_activations(state, activated_ids, context.event_meta.event_id)
        echo_instructions = delta_agent.generate_echo_instructions(state, echo_compatible)

        release = (
            phase == PhaseType.CONFRONTATION
            and deviation_analysis is not None
            and deviation_analysis.release
        )
        if release:
            self._log_generation(context, loop_result.tool_results, "", False, True)
            return NarrativeGenerationResult(
                narrative="",
                awaiting_input=False,
                phase_complete=True,
                delta_fact=deviation_analysis.delta_fact,
                delta_intensity=deviation_analysis.delta_intensity,
                activated_delta_ids=activated_ids,
                echo_completed_ids=echo_compatible,
                adaptation_plan=adaptation_plan_raw,
                deviation_analysis=deviation_analysis,
            )

        writing_guidance = loop_result.orchestrator_meta.get("writing_guidance", "")

        if echo_instructions:
            writing_guidance += f"\n\n【Echo 告别】\n{echo_instructions}"

        if phase != PhaseType.CONFRONTATION or not context.player_input:
            n = len(context.phase_source)
            lo, hi = int(n * 0.85), int(n * 1.15)
            writing_guidance += f"\n\n【字数目标】{lo}-{hi} 字（原文 {n} 字）"

        if phase == PhaseType.CONFRONTATION and history_text:
            writing_guidance += f"\n\n【已叙述内容】\n{history_text}"

        is_continuation = phase == PhaseType.CONFRONTATION and context.player_input
        writer_input = WriterInput(
            phase_source="" if is_continuation else context.phase_source,
            writing_guidance=writing_guidance,
        )

        try:
            on_chunk = kwargs.get("on_chunk")
            narrative = self._writer.generate(writer_input, on_chunk=on_chunk)
        except Exception as e:
            self._log_error(context, loop_result.tool_results, writer_input, e)
            raise

        if phase == PhaseType.SETUP:
            awaiting_input, phase_complete = True, True
        elif phase == PhaseType.RESOLUTION:
            awaiting_input, phase_complete = False, True
        else:
            no_deviation = deviation_analysis is None and context.player_input
            awaiting_input = not no_deviation
            phase_complete = no_deviation

        self._log_generation(context, loop_result.tool_results, narrative, awaiting_input, phase_complete)

        return NarrativeGenerationResult(
            narrative=narrative,
            awaiting_input=awaiting_input,
            phase_complete=phase_complete,
            delta_fact=deviation_analysis.delta_fact if deviation_analysis else None,
            delta_intensity=deviation_analysis.delta_intensity if deviation_analysis else None,
            activated_delta_ids=activated_ids,
            echo_completed_ids=echo_compatible,
            adaptation_plan=adaptation_plan_raw,
            deviation_analysis=deviation_analysis,
        )

    def _handle_tool_call(
        self,
        tool_call: ToolCall,
        context: AgentContext,
        state: GameState,
        captured: dict,
        captured_lock: threading.Lock,
    ) -> ToolResult:
        if tool_call.name == "recall_history":
            return self._agent_executor.get("context_enrichment").recall_history(
                state,
                tool_call.arguments.get("query", ""),
                context.event_meta.event_id,
            )

        if tool_call.name == "query_entities":
            raw_text = tool_call.arguments.get("text", "")
            text = " ".join(raw_text) if isinstance(raw_text, list) else str(raw_text)
            return self._agent_executor.get("context_enrichment").query_entities(text)

        if tool_call.name == "check_deviation":
            if not context.player_input:
                return ToolResult(
                    tool_name="check_deviation",
                    content="玩家输入为空，该调用已被拦截。",
                )
            result = self._agent_executor.get("deviation_guidance").check_deviation(
                state, context.event_context, tool_call.arguments,
            )
            with captured_lock:
                captured["deviation_analysis"] = result.analysis
            if result.analysis and result.analysis.release:
                return ToolResult(tool_name="deviation_release", content=result.tool_result.content)
            return result.tool_result

        if tool_call.name == "request_bridge":
            with captured_lock:
                captured["bridge_conflicts"] = tool_call.arguments.get("conflicts", [])
            return ToolResult(tool_name="request_bridge", content="<bridge_requested/>")

        if tool_call.name == "request_adaptation":
            return self._handle_adaptation(
                tool_call, context, state, captured, captured_lock,
            )

        return ToolResult(
            tool_name=tool_call.name,
            content=f"<error>Unknown tool: {tool_call.name}</error>",
        )

    def _log_generation(self, context, tool_results, narrative: str, awaiting_input: bool, phase_complete: bool) -> None:
        glog.log("AGENT_EXEC", {
            "agent": "narrative_generation",
            "action": "generation_complete",
            "phase": context.phase.value,
            "player_input": context.player_input,
            "tools_called": list(tool_results.keys()),
            "tool_results": {
                k: v.content if hasattr(v, "content") else str(v)
                for k, v in tool_results.items()
            },
            "narrative": narrative,
            "awaiting_input": awaiting_input,
            "phase_complete": phase_complete,
        })

    def _handle_adaptation(
        self,
        tool_call: ToolCall,
        context: AgentContext,
        state: GameState,
        captured: dict,
        captured_lock: threading.Lock,
    ) -> ToolResult:
        delta_ids = tool_call.arguments.get("delta_ids", [])
        if not delta_ids:
            return ToolResult(
                tool_name="request_adaptation",
                content="<adaptation_result>无需适配</adaptation_result>",
            )

        id_set = set(delta_ids)
        active_deltas = [d for d in state.delta_state.get_active_deltas() if d.delta_id in id_set]
        if not active_deltas:
            return ToolResult(
                tool_name="request_adaptation",
                content="<adaptation_result>无需适配</adaptation_result>",
            )

        archived_ids = set(tool_call.arguments.get("archived_ids", []))
        archived_text = ""
        if archived_ids:
            selected = [d for d in state.delta_state.archived_deltas if d.delta_id in archived_ids]
            if selected:
                archived_text = "\n".join(
                    f"- {d.archived_summary or d.fact[:30]}（{d.source_event}）"
                    for d in selected
                )

        scene_agent = self._agent_executor.get("scene_adaptation")
        plan = scene_agent.adapt_scene(
            event_id=context.event_meta.event_id,
            event_original_text=captured["event_original_text"],
            active_deltas=active_deltas,
            archived_overrides_text=archived_text,
        )

        if plan.adaptations:
            raw = [a.model_dump() for a in plan.adaptations]
            formatted = _render_adaptation_plan_tags(raw)
            with captured_lock:
                captured["adaptation_plan_text"] = formatted
                captured["adaptation_plan_raw"] = raw
            return ToolResult(
                tool_name="request_adaptation",
                content=f"<adaptation_result>\n{formatted}\n</adaptation_result>",
            )

        return ToolResult(
            tool_name="request_adaptation",
            content="<adaptation_result>无适配指令</adaptation_result>",
        )

    def _log_error(self, context, tool_results, writer_input, error) -> None:
        glog.log("ERROR", {
            "agent": "narrative_generation",
            "action": "writer_failed",
            "phase": context.phase.value,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "writer_input": writer_input.model_dump() if hasattr(writer_input, "model_dump") else str(writer_input),
            "tool_results": {
                k: v.content if hasattr(v, "content") else str(v)
                for k, v in tool_results.items()
            },
            "player_input": context.player_input,
            "phase_source": context.phase_source,
        })


_PROMPTS_DIR = Path(__file__).parent / "orchestrator" / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _render_adaptation_plan_tags(raw_list: list[dict]) -> str:
    parts = ["<adaptation_plan>"]
    for item in raw_list:
        strategy = "+".join(item["strategies"])
        intensity = item["intensity_guidance"]
        delta_src = item["delta_source"]
        parts.append(f'<adaptation strategy="{strategy}" intensity="{intensity}" delta_source="{delta_src}">')
        parts.append(f"  <target>{item['target']}</target>")
        if item.get("original"):
            parts.append(f"  <original>{item['original']}</original>")
        parts.append(f"  <plan>{item['plan']}</plan>")
        parts.append("</adaptation>")
    parts.append("</adaptation_plan>")
    return "\n".join(parts)
