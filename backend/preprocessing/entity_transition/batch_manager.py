from __future__ import annotations

import json
from dataclasses import dataclass

import config
from .token_estimator import TokenEstimator


@dataclass
class BatchInfo:
    events: list[dict]
    event_ids: set[str]
    registry_subset: dict
    candidates_subset: dict[str, list[dict]]
    overlap_count: int


class BatchManager:

    def __init__(
        self,
        token_estimator: TokenEstimator,
        fixed_costs: dict[str, int],
        budget_config: config.TokenBudgetConfig | None = None,
    ):
        self._estimator = token_estimator
        self._fixed_costs = fixed_costs
        self._budget_config = budget_config or config.STAGE3_TOKEN_BUDGET

        self._raw_budget = min(
            self._budget_config.necessity_grader,
            self._budget_config.transition_annotator,
            self._budget_config.cross_validator,
        )
        self._effective_budget = self._estimator.effective_budget(self._raw_budget)
        self._hard_cap = self._estimator.effective_budget(
            self._budget_config.hard_cap
        )

    def create_batches(
        self,
        events_slim: list[dict],
        candidates: dict[str, list[dict]],
        registry: dict,
    ) -> list[BatchInfo]:
        if not events_slim:
            return []

        event_token_costs: list[int] = []
        event_entity_ids: list[set[str]] = []

        for event in events_slim:
            eid = event["id"]
            event_cost = self._estimator.count_tokens(
                json.dumps(event, ensure_ascii=False)
            )
            cand_list = candidates.get(eid, [])
            if cand_list:
                cand_cost = self._estimator.count_tokens(
                    json.dumps(cand_list, ensure_ascii=False)
                )
            else:
                cand_cost = 0
            event_token_costs.append(event_cost + cand_cost)
            event_entity_ids.append({c["id"] for c in cand_list})

        entity_token_map: dict[str, int] = {}
        for category in ("characters", "locations", "items", "knowledge"):
            for entity in registry.get(category, []):
                entity_token_map[entity["id"]] = self._estimator.count_tokens(
                    json.dumps(entity, ensure_ascii=False)
                )

        fixed_cost = max(self._fixed_costs.values())
        budget = self._effective_budget

        batches: list[BatchInfo] = []
        start = 0
        prev_overlap = 0

        while start < len(events_slim):
            current_tokens = fixed_cost
            current_entities: set[str] = set()
            end = start

            while end < len(events_slim):
                new_entities = event_entity_ids[end] - current_entities
                registry_delta = sum(
                    entity_token_map.get(eid, 0) for eid in new_entities
                )
                event_total = event_token_costs[end] + registry_delta
                tokens_with = current_tokens + event_total

                if tokens_with > budget and end > start:
                    tokens_without = current_tokens
                    diff_with = abs(tokens_with - budget)
                    diff_without = abs(tokens_without - budget)

                    if diff_with < diff_without and tokens_with <= self._hard_cap:
                        current_tokens = tokens_with
                        current_entities |= new_entities
                        end += 1

                    end = self._find_cut_point(events_slim, start, end)
                    break

                current_tokens = tokens_with
                current_entities |= new_entities
                end += 1

            batch_events = events_slim[start:end]
            batch_event_ids = {e["id"] for e in batch_events}

            batch_entity_ids: set[str] = set()
            for i in range(start, end):
                batch_entity_ids |= event_entity_ids[i]

            batch_info = BatchInfo(
                events=batch_events,
                event_ids=batch_event_ids,
                registry_subset=self._prune_registry(registry, batch_entity_ids),
                candidates_subset={
                    eid: cands
                    for eid, cands in candidates.items()
                    if eid in batch_event_ids
                },
                overlap_count=prev_overlap,
            )
            batches.append(batch_info)

            if end >= len(events_slim):
                break

            prev_overlap = self._compute_overlap(event_token_costs, start, end)
            start = end - prev_overlap

        return batches

    def merge_results(
        self,
        batch_results: list[list[dict]],
        batch_infos: list[BatchInfo],
    ) -> list[dict]:
        if len(batch_results) <= 1:
            return batch_results[0] if batch_results else []

        merged = list(batch_results[0])
        for i in range(1, len(batch_results)):
            overlap = batch_infos[i].overlap_count
            merged.extend(batch_results[i][overlap:])
        return merged

    @staticmethod
    def _find_cut_point(
        events_slim: list[dict], start: int, end: int
    ) -> int:
        for offset in range(-5, 1):
            candidate = end + offset
            if start < candidate < len(events_slim):
                if events_slim[candidate].get("type") == "narrative":
                    return candidate
        return end

    @staticmethod
    def _prune_registry(registry: dict, entity_ids: set[str]) -> dict:
        return {
            category: [
                entity
                for entity in registry.get(category, [])
                if entity["id"] in entity_ids
            ]
            for category in ("characters", "locations", "items", "knowledge")
        }

    def _compute_overlap(
        self, event_token_costs: list[int], start: int, end: int
    ) -> int:
        if end <= start:
            return 0

        bc = self._budget_config
        max_overlap_tokens = int(self._effective_budget * bc.overlap_budget_ratio)

        overlap_count = min(bc.default_overlap, end - start - 1)
        if overlap_count <= 0:
            return 0

        overlap_tokens = sum(event_token_costs[end - overlap_count : end])
        if overlap_tokens <= max_overlap_tokens:
            return overlap_count

        overlap_count = min(bc.min_overlap, end - start - 1)
        return max(overlap_count, 0)
