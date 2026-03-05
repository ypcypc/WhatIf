from typing import Any

from core.models import EventImportance
from runtime.agents.deviation_guidance.deviation_controller import DeviationController
from runtime.agents.models import AgentResult, EventContext, ToolResult, DeviationAnalysis
from runtime.agents.base import BaseAgent, GameState
from runtime.game_logger import glog


class DeviationGuidanceResult(AgentResult):

    analysis: DeviationAnalysis | None = None
    tool_result: ToolResult | None = None


class DeviationGuidanceAgent(BaseAgent):

    def __init__(self, deviation_controller: DeviationController):
        self._ctrl = deviation_controller

    def check_deviation(
        self,
        state: GameState,
        event_context: EventContext,
        arguments: dict[str, Any],
    ) -> DeviationGuidanceResult:
        required = ["event_id", "goal", "player_input", "importance"]
        for param in required:
            if param not in arguments:
                return DeviationGuidanceResult(
                    success=False,
                    tool_result=ToolResult(
                        tool_name="check_deviation",
                        content=f"<deviation_check><error>Missing {param}</error></deviation_check>",
                    ),
                )

        try:
            importance = EventImportance(arguments["importance"])
        except (ValueError, KeyError):
            importance = EventImportance.NORMAL

        delta_context = state.delta_state.format_delta_context()

        output = self._ctrl.analyze(
            event_id=arguments["event_id"],
            history=list(event_context.deviation_history),
            goal=arguments["goal"],
            player_input=arguments["player_input"],
            importance=importance,
            context="无额外上下文",
            delta_context=delta_context,
        )

        analysis = DeviationAnalysis(
            scratch=output.scratch,
            is_deviation=output.is_deviation,
            has_world_change=output.has_world_change,
            persistence_count=output.persistence_count,
            release=output.release,
            guidance_method=output.guidance_method,
            guidance_tone=output.guidance_tone,
            guidance_hint=output.guidance_hint,
            delta_fact=output.delta_fact,
            delta_intensity=output.delta_intensity,
        )

        tool_result = ToolResult(
            tool_name="check_deviation",
            content=_format_deviation(output),
        )

        glog.log("TOOL_CALL", {
            "agent": "deviation_guidance",
            "tool": "check_deviation",
            "event_id": arguments.get("event_id"),
            "is_deviation": output.is_deviation,
            "has_world_change": output.has_world_change,
            "persistence_count": output.persistence_count,
            "release": output.release,
            "guidance_method": output.guidance_method,
            "delta_fact": output.delta_fact,
            "delta_intensity": output.delta_intensity,
        })

        return DeviationGuidanceResult(
            analysis=analysis,
            tool_result=tool_result,
        )


def _format_deviation(result: Any) -> str:
    lines = [
        "<deviation_check>",
        f"  <scratch>{result.scratch}</scratch>",
        f"  <is_deviation>{str(result.is_deviation).lower()}</is_deviation>",
        f"  <has_world_change>{str(result.has_world_change).lower()}</has_world_change>",
        f"  <persistence_count>{result.persistence_count}</persistence_count>",
        f"  <release>{str(result.release).lower()}</release>",
        f"  <guidance_method>{result.guidance_method}</guidance_method>",
        f"  <guidance_tone>{result.guidance_tone}</guidance_tone>",
        f"  <guidance_hint>{result.guidance_hint}</guidance_hint>",
    ]
    if result.delta_fact:
        lines.append(f"  <delta_fact>{result.delta_fact}</delta_fact>")
    if result.delta_intensity is not None:
        lines.append(f"  <delta_intensity>{result.delta_intensity}</delta_intensity>")
    lines.append("</deviation_check>")
    return "\n".join(lines)
