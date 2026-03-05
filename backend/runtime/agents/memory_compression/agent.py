import threading
from concurrent.futures import ThreadPoolExecutor

from runtime.agents.memory_compression.l0_compressor import L0Compressor
from runtime.agents.memory_compression.l1_compressor import L1Compressor
from runtime.agents.models import L0Summary
from runtime.agents.base import BaseAgent, GameState
from runtime.game_logger import glog


class MemoryCompressionAgent(BaseAgent):

    L1_THRESHOLD = 10

    def __init__(
        self,
        l0_compressor: L0Compressor,
        l1_compressor: L1Compressor,
    ):
        self._l0 = l0_compressor
        self._l1 = l1_compressor
        self._thread_pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="compression",
        )
        self._lock = threading.Lock()
        self._l1_counter = 0

    def compress_event_sync_l0(
        self,
        state: GameState,
        event_id: str,
        event_content: str,
    ) -> L0Summary:
        l0_summary = self._l0.compress(event_id, event_content)

        with self._lock:
            state.l0_summaries.append(l0_summary)

        glog.log("COMPRESSION", {
            "action": "l0_complete",
            "event_id": event_id,
            "summary_len": len(l0_summary.summary),
            "summary": l0_summary.summary,
        })

        self._thread_pool.submit(self._maybe_create_l1, state)
        return l0_summary

    def _maybe_create_l1(self, state: GameState) -> None:
        with self._lock:
            l0_in_l1 = sum(len(l1.l0_summaries) for l1 in state.l1_summaries)
            pending_l0s = state.l0_summaries[l0_in_l1:]

            if len(pending_l0s) < self.L1_THRESHOLD:
                return

            l0s_to_summarize = pending_l0s[: self.L1_THRESHOLD]
            self._l1_counter += 1
            l1_id = f"L1-{self._l1_counter:03d}"

        try:
            l1_summary = self._l1.compress(l1_id, l0s_to_summarize)

            with self._lock:
                state.l1_summaries.append(l1_summary)

            glog.log("COMPRESSION", {
                "action": "l1_complete",
                "l1_id": l1_id,
                "covers": l1_summary.covers,
                "summary": l1_summary.summary,
            })

        except Exception as e:
            glog.log("ERROR", {
                "agent": "memory_compression",
                "action": "l1_failed",
                "l1_id": l1_id,
                "error": str(e),
            })

    def flush(self) -> None:
        barrier = self._thread_pool.submit(lambda: None)
        barrier.result(timeout=60)

    def shutdown(self) -> None:
        self._thread_pool.shutdown(wait=True)
        glog.log("COMPRESSION", {"action": "shutdown"})

    @property
    def l1_counter(self) -> int:
        return self._l1_counter

    @l1_counter.setter
    def l1_counter(self, value: int) -> None:
        self._l1_counter = value

    def get_save_state(self) -> dict:
        return {"l1_counter": self._l1_counter}

    def restore_save_state(self, data: dict) -> None:
        self._l1_counter = data.get("l1_counter", 0)
