from runtime.agents.base import AgentContext
from runtime.agents.delta_lifecycle.agent import DeltaContextResult


def build_orchestrator_input(
    template: str,
    context: AgentContext,
    delta_ctx: DeltaContextResult,
    history_text: str = "",
) -> str:
    return (
        template
        .replace("{phase_source}", context.phase_source_decision)
        .replace("{setup_narrative}", context.event_context.setup_narrative or "")
        .replace("{confrontation_history}", history_text)
        .replace("{active_deltas}", delta_ctx.active_tags)
        .replace("{already_activated}", delta_ctx.already_activated)
        .replace("{pending_echo}", delta_ctx.pending_echo_tags)
        .replace("{archived_overrides}", delta_ctx.archived_text)
        .replace("{previous_event}", context.previous_event or "")
        .replace("{player_input}", context.player_input or "[无玩家输入——开篇叙事阶段，禁止调用 check_deviation]")
        .replace("{event_id}", context.event_meta.event_id)
        .replace("{importance}", context.event_meta.importance)
        .replace("{goal}", context.event_meta.goal or "")
        .replace("{soft_guide_hints}", "\n".join(f"- {h}" for h in context.event_meta.soft_guide_hints) or "无")
        .replace("{event_type}", context.event_meta.event_type)
        .replace("{preconditions}", _format_preconditions(context.event_meta.preconditions))
    )


def _format_preconditions(preconditions: list[dict]) -> str:
    if not preconditions:
        return "无"
    lines = [
        f'- {p["name"]}（{p["type"]}）的{p["attribute"]}必须为 {p["from"]}'
        for p in preconditions
        if p.get("from") is not None
    ]
    return "\n".join(lines) or "无"


def format_confrontation_history(history: list) -> str:
    if not history:
        return ""
    lines = []
    for entry in history:
        if hasattr(entry, "player_input"):
            if entry.player_input:
                lines.append(f"[player] {entry.player_input}")
            if entry.response_summary:
                lines.append(f"[system] {entry.response_summary}")
        elif isinstance(entry, dict):
            lines.append(f"[{entry.get('role', 'unknown')}] {entry.get('content', '')}")
    return "\n".join(lines)
