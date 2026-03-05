import json
from typing import Any

from runtime.agents.context_enrichment.history_recall import HistoryRecaller
from runtime.agents.context_enrichment.entity_recognizer import EntityRecognizerAgent
from runtime.agents.models import ToolResult
from runtime.tools.lorebook_query import LorebookQuery
from runtime.agents.base import BaseAgent, GameState
from runtime.game_logger import glog


class ContextEnrichmentAgent(BaseAgent):

    def __init__(
        self,
        history_agent: HistoryRecaller,
        entity_agent: EntityRecognizerAgent,
        lorebook_query: LorebookQuery,
        lorebook_content: str,
    ):
        self._history = history_agent
        self._entity = entity_agent
        self._lorebook = lorebook_query
        self._lorebook_content = lorebook_content

    def recall_history(
        self,
        state: GameState,
        query: str,
        current_event_id: str | None,
    ) -> ToolResult:
        if not query:
            return ToolResult(
                tool_name="recall_history",
                content="<recalled_events><error>Missing query parameter</error></recalled_events>",
            )

        l0_in_l1 = sum(len(l1.l0_summaries) for l1 in state.l1_summaries)
        pending_l0s = state.l0_summaries[l0_in_l1:]

        result = self._history.recall(
            query=query,
            l1_summaries=state.l1_summaries,
            pending_l0s=pending_l0s,
            current_event_id=current_event_id,
            output_root_tag="recalled_events",
        )

        glog.log("TOOL_CALL", {
            "agent": "context_enrichment",
            "tool": "recall_history",
            "query": query,
            "event_id": current_event_id,
            "has_result": bool(result.restored_context),
            "result": result.restored_context,
        })

        if not result.restored_context:
            return ToolResult(
                tool_name="recall_history",
                content="<recalled_events><empty>No relevant history found</empty></recalled_events>",
            )

        return ToolResult(tool_name="recall_history", content=result.restored_context)

    def query_entities(self, text: str) -> ToolResult:
        if not text:
            return ToolResult(
                tool_name="query_entities",
                content="<entities><error>Missing text parameter</error></entities>",
            )

        recognition = self._entity.run(
            text=text,
            lorebook_content=self._lorebook_content,
        )

        glog.log("TOOL_CALL", {
            "agent": "context_enrichment",
            "tool": "query_entities",
            "text": text,
            "entity_ids": recognition.entity_ids,
        })

        if not recognition.entity_ids:
            return ToolResult(
                tool_name="query_entities",
                content="<entities><empty>No entities recognized</empty></entities>",
            )

        entities = self._lorebook.get_many(recognition.entity_ids)
        return ToolResult(
            tool_name="query_entities",
            content=_format_entities(entities),
        )


def _format_entities(entities: list[dict[str, Any]]) -> str:
    parts = ["<entities>"]
    for e in entities:
        parts.append(f'<entity id="{e["id"]}" type="{e["type"]}">')
        parts.append(json.dumps(e["data"], ensure_ascii=False, indent=2))
        parts.append("</entity>")
    parts.append("</entities>")
    return "\n".join(parts)
