from enum import Enum

from pydantic import BaseModel, Field


class DeltaStatus(str, Enum):
    ACTIVE = "active"
    ECHOING = "echoing"
    ARCHIVED = "archived"


class DeltaCategory(str, Enum):
    STATE = "state"
    PROCESS = "process"


class DeltaEntry(BaseModel):
    delta_id: str
    fact: str = Field(description="客观事实陈述，≤ 80字")
    source_event: str
    canon_override: str = Field(description="它覆盖了原著中的什么")
    intensity: int = Field(ge=0, le=5, default=5)
    status: DeltaStatus = DeltaStatus.ACTIVE
    category: DeltaCategory = DeltaCategory.STATE
    last_activated_event: str = ""
    archived_summary: str = ""
    creation_order: int = 0


class DeltaStateManager:

    MAX_ACTIVE = 5
    MAX_ECHO_QUEUE = 2
    ECHO_TIMEOUT = 10

    def __init__(self):
        self.delta_entries: list[DeltaEntry] = []
        self.archived_deltas: list[DeltaEntry] = []
        self.pending_echo_queue: list[str] = []
        self.event_activated_deltas: set[str] = set()
        self._next_id: int = 1
        self._echo_wait_counter: dict[str, int] = {}
        self._delta_index: dict[str, DeltaEntry] = {}

    def create_delta(
        self,
        fact: str,
        source_event: str,
        canon_override: str = "",
        intensity: int = 5,
    ) -> DeltaEntry:
        active_count = sum(
            1 for d in self.delta_entries
            if d.status in (DeltaStatus.ACTIVE, DeltaStatus.ECHOING)
        )
        while active_count >= self.MAX_ACTIVE:
            self._evict_lru()
            active_count = sum(
                1 for d in self.delta_entries
                if d.status in (DeltaStatus.ACTIVE, DeltaStatus.ECHOING)
            )

        delta_id = f"delta-{self._next_id:03d}"
        self._next_id += 1

        entry = DeltaEntry(
            delta_id=delta_id,
            fact=fact[:80],
            source_event=source_event,
            canon_override=canon_override[:100],
            intensity=min(max(intensity, 1), 5),
            last_activated_event=source_event,
            creation_order=self._next_id - 1,
        )
        self.delta_entries.append(entry)
        self._delta_index[delta_id] = entry
        return entry

    def mark_activated(self, delta_id: str, current_event: str) -> None:
        entry = self._find(delta_id)
        if not entry or entry.status not in (DeltaStatus.ACTIVE, DeltaStatus.ECHOING):
            return
        entry.last_activated_event = current_event
        self.event_activated_deltas.add(delta_id)

    def decay_event_activations(self, current_event: str) -> None:
        for delta_id in list(self.event_activated_deltas):
            entry = self._find(delta_id)
            if not entry or entry.status != DeltaStatus.ACTIVE:
                continue
            entry.intensity = max(0, entry.intensity - 1)
            entry.last_activated_event = current_event
            if entry.intensity == 0:
                self._enqueue_echo(entry)

    def reset_event_activations(self) -> None:
        self.event_activated_deltas.clear()

    def complete_echo(self, delta_id: str) -> None:
        entry = self._find(delta_id)
        if not entry:
            return
        self._archive(entry)

    def tick_echo_timeouts(self) -> None:
        timed_out = []
        for did in list(self.pending_echo_queue):
            self._echo_wait_counter[did] = self._echo_wait_counter.get(did, 0) + 1
            if self._echo_wait_counter[did] > self.ECHO_TIMEOUT:
                timed_out.append(did)
        for did in timed_out:
            self._silent_archive(did)

        while len(self.pending_echo_queue) > self.MAX_ECHO_QUEUE:
            oldest_id = self.pending_echo_queue.pop(0)
            self._silent_archive(oldest_id)

    def evolve_delta(self, delta_id: str, new_fact: str, new_intensity: int) -> DeltaEntry | None:
        entry = self._find(delta_id)
        if not entry or entry.status != DeltaStatus.ACTIVE:
            return None
        entry.fact = new_fact[:80]
        entry.intensity = min(max(new_intensity, 1), 5)
        return entry

    def get_active_deltas(self) -> list[DeltaEntry]:
        return [d for d in self.delta_entries if d.status == DeltaStatus.ACTIVE]

    def get_echoing_deltas(self) -> list[DeltaEntry]:
        return [d for d in self.delta_entries if d.status == DeltaStatus.ECHOING]

    def format_active_tags(self, include_echoing: bool = False) -> str:
        entries = self.get_active_deltas()
        if include_echoing:
            entries = entries + self.get_echoing_deltas()
        if not entries:
            return ""
        lines = []
        for d in entries:
            lines.append(
                f'<delta id="{d.delta_id}" intensity="{d.intensity}" '
                f'status="{d.status.value}">{d.fact}</delta>'
            )
        return "\n".join(lines)

    def format_pending_echo_tags(self) -> str:
        echoing = [
            d for d in self.delta_entries
            if d.status == DeltaStatus.ECHOING and d.delta_id in self.pending_echo_queue
        ]
        if not echoing:
            return ""
        lines = []
        for d in echoing:
            lines.append(f'<echo delta_id="{d.delta_id}" fact="{d.fact}"/>')
        return "\n".join(lines)

    def format_archived_text(self) -> str:
        if not self.archived_deltas:
            return ""
        lines = []
        for d in self.archived_deltas:
            summary = d.archived_summary or d.fact[:30]
            lines.append(f'<archived id="{d.delta_id}">{summary}（{d.source_event}）</archived>')
        return "\n".join(lines)

    def format_echo_instructions_tags(self, compatible_ids: list[str]) -> str:
        if not compatible_ids:
            return ""
        lines = []
        for did in compatible_ids:
            entry = self._find(did)
            if not entry:
                continue
            lines.append(
                f'<echo_instruction target_delta="{did}">\n'
                f'心愿"{entry.fact}"即将淡出叙事焦点。\n'
                f'请在本段叙事中的某个自然时刻，安排一个简短的回顾或告别：\n'
                f'- 形式可以是：角色的一句感慨、一个象征性的小动作、一段回忆、一件信物的交接\n'
                f'- 应让玩家感受到这个选择曾经有过意义\n'
                f'- 篇幅严格控制在 2-3 句话，不要喧宾夺主\n'
                f'- 重要：不要让相关角色死亡或物件损毁——事实仍然为真，只是不再是叙事的关注重点\n'
                f'</echo_instruction>'
            )
        return "\n".join(lines)

    def format_delta_context(self) -> str:
        parts = []

        active = self.get_active_deltas()
        if active:
            parts.append("[当前生效的现实改动（Delta State）]")
            parts.append("以下事实已被玩家在之前的事件中改写，现在是故事的基准现实：")
            for d in active:
                parts.append(f"- {d.fact}（{d.delta_id}, 强度:{d.intensity}/5, 来源:{d.source_event}）")

        echoing = self.get_echoing_deltas()
        if echoing:
            parts.append("\n[正在淡出的现实改动（Echoing）]")
            parts.append("以下事实即将淡出叙事焦点，但仍然为真：")
            for d in echoing:
                parts.append(f"- {d.fact}（{d.delta_id}, 来源:{d.source_event}）")

        archived = self.archived_deltas
        if archived:
            parts.append("\n[历史归档改动]")
            parts.append("以下是更早期的玩家改动，虽已淡出叙事焦点但仍为真：")
            for d in archived:
                summary = d.archived_summary or d.fact[:30]
                parts.append(f"- {summary}（{d.source_event}）")

        return "\n".join(parts) if parts else ""

    def to_dict(self) -> dict:
        return {
            "delta_entries": [d.model_dump() for d in self.delta_entries],
            "archived_deltas": [d.model_dump() for d in self.archived_deltas],
            "pending_echo_queue": self.pending_echo_queue,
            "event_activated_deltas": list(self.event_activated_deltas),
            "_next_id": self._next_id,
            "_echo_wait_counter": self._echo_wait_counter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeltaStateManager":
        mgr = cls()
        mgr.delta_entries = [
            DeltaEntry.model_validate(d) for d in data.get("delta_entries", [])
        ]
        mgr.archived_deltas = [
            DeltaEntry.model_validate(d) for d in data.get("archived_deltas", [])
        ]
        mgr.pending_echo_queue = data.get("pending_echo_queue", [])
        mgr.event_activated_deltas = set(data.get("event_activated_deltas", []))
        mgr._next_id = data.get("_next_id", 1)
        mgr._echo_wait_counter = data.get("_echo_wait_counter", {})
        mgr._delta_index = {d.delta_id: d for d in mgr.delta_entries}
        return mgr

    def _find(self, delta_id: str) -> DeltaEntry | None:
        return self._delta_index.get(delta_id)

    def _enqueue_echo(self, entry: DeltaEntry) -> None:
        while len(self.pending_echo_queue) >= self.MAX_ECHO_QUEUE:
            oldest_id = self.pending_echo_queue.pop(0)
            self._silent_archive(oldest_id)

        entry.status = DeltaStatus.ECHOING
        self.pending_echo_queue.append(entry.delta_id)
        self._echo_wait_counter[entry.delta_id] = -1

    def _evict_lru(self) -> None:
        active = [d for d in self.delta_entries if d.status == DeltaStatus.ACTIVE]
        if not active:
            echoing = [d for d in self.delta_entries if d.status == DeltaStatus.ECHOING]
            if not echoing:
                return
            victim = min(echoing, key=lambda d: d.creation_order)
        else:
            victim = min(active, key=lambda d: d.creation_order)
        self._silent_archive(victim.delta_id)

    def _archive(self, entry: DeltaEntry) -> None:
        entry.status = DeltaStatus.ARCHIVED
        if not entry.archived_summary:
            entry.archived_summary = entry.fact[:30]
        if entry.delta_id in self.pending_echo_queue:
            self.pending_echo_queue.remove(entry.delta_id)
        self._echo_wait_counter.pop(entry.delta_id, None)
        self._delta_index.pop(entry.delta_id, None)
        if entry in self.delta_entries:
            self.delta_entries.remove(entry)
        if entry not in self.archived_deltas:
            self.archived_deltas.append(entry)

    def _silent_archive(self, delta_id: str) -> None:
        entry = self._find(delta_id)
        if not entry:
            return
        self._archive(entry)
