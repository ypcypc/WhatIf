from typing import Optional

from core.llm import LLMClient
from runtime.agents.context_enrichment.l1_recall import L1RecallAgent
from runtime.agents.context_enrichment.l0_recall import L0RecallAgent
from runtime.agents.models import (
    L0Summary,
    L1Summary,
    L1SelectionOutput,
    L0SelectionOutput,
    RecallResult,
)


class HistoryRecaller:

    L1_THRESHOLD = 10

    def __init__(self, llm_client: LLMClient):
        self.l1_agent = L1RecallAgent(llm_client)
        self.l0_agent = L0RecallAgent(llm_client)

    def recall(
        self,
        query: str,
        l1_summaries: list[L1Summary],
        pending_l0s: list[L0Summary],
        current_event_id: Optional[str] = None,
        output_root_tag: str = "history_context",
    ) -> RecallResult:
        if current_event_id:
            pending_l0s = [l0 for l0 in pending_l0s if l0.event_id != current_event_id]

        total_events = sum(len(l1.l0_summaries) for l1 in l1_summaries) + len(pending_l0s)

        if total_events < self.L1_THRESHOLD or not l1_summaries:
            candidate_l0s = self._collect_all_l0s(l1_summaries, pending_l0s)
            return self._l0_filter_and_restore(query, candidate_l0s, output_root_tag)

        l1_result: L1SelectionOutput = self.l1_agent.select(
            query=query,
            l1_summaries=l1_summaries,
            pending_l0s=pending_l0s,
        )

        candidate_l0s = self._expand_l1_selection(
            l1_result=l1_result,
            l1_summaries=l1_summaries,
            pending_l0s=pending_l0s,
        )

        if not candidate_l0s and pending_l0s:
            candidate_l0s = pending_l0s.copy()

        return self._l0_filter_and_restore(query, candidate_l0s, output_root_tag)

    def _collect_all_l0s(
        self,
        l1_summaries: list[L1Summary],
        pending_l0s: list[L0Summary],
    ) -> list[L0Summary]:
        all_l0s = []
        for l1 in l1_summaries:
            all_l0s.extend(l1.l0_summaries)
        all_l0s.extend(pending_l0s)
        return all_l0s

    def _expand_l1_selection(
        self,
        l1_result: L1SelectionOutput,
        l1_summaries: list[L1Summary],
        pending_l0s: list[L0Summary],
    ) -> list[L0Summary]:
        l0s = []

        l1_map = {l1.id: l1 for l1 in l1_summaries}

        for l1_id in l1_result.selected_l1_ids:
            if l1_id in l1_map:
                l0s.extend(l1_map[l1_id].l0_summaries)

        pending_map = {l0.event_id: l0 for l0 in pending_l0s}
        for event_id in l1_result.selected_pending_ids:
            if event_id in pending_map:
                l0s.append(pending_map[event_id])

        return l0s

    def _l0_filter_and_restore(
        self,
        query: str,
        candidate_l0s: list[L0Summary],
        output_root_tag: str,
    ) -> RecallResult:
        if not candidate_l0s:
            return RecallResult(restored_context="")

        l0_result: L0SelectionOutput = self.l0_agent.select(
            query=query,
            candidate_l0s=candidate_l0s,
        )

        if not l0_result.selected_event_ids:
            return RecallResult(restored_context="")

        l0_map = {l0.event_id: l0 for l0 in candidate_l0s}

        restored_context = self._restore_context(
            l0_result.selected_event_ids,
            l0_map,
            output_root_tag,
        )

        return RecallResult(restored_context=restored_context)

    def _restore_context(
        self,
        selected_ids: list[str],
        l0_map: dict[str, L0Summary],
        root_tag: str,
    ) -> str:
        parts = [f"<{root_tag}>"]

        for event_id in selected_ids:
            if event_id not in l0_map:
                continue

            l0 = l0_map[event_id]
            parts.append(f'<event id="{event_id}" tags="{", ".join(l0.tags)}">')
            parts.append(l0.summary)
            parts.append("</event>")

        parts.append(f"</{root_tag}>")

        return "\n".join(parts)
