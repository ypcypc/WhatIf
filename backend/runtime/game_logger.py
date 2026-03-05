
import json
import sys
import threading
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path

import config

_RED = "\033[91m"
_RESET = "\033[0m"


class GameLogger:

    def __init__(self) -> None:
        self._file: TextIOWrapper | None = None
        self._lock = threading.Lock()
        self._session_id: str = ""

    def start_session(self, action: str = "unknown") -> Path | None:
        if not config.SESSION_LOG_ENABLED:
            return None

        self.end_session()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_id = f"{ts}_{action}"
        log_dir: Path = config.SESSION_LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"session_{self._session_id}.jsonl"
        self._file = open(log_path, "a", encoding="utf-8")
        self.log("SESSION", {"action": "start", "session_id": self._session_id})
        return log_path

    def end_session(self) -> None:
        if self._file:
            self.log("SESSION", {"action": "end", "session_id": self._session_id})
            self._file.close()
            self._file = None

    def log(self, category: str, data: dict) -> None:
        if not config.SESSION_LOG_ENABLED or not self._file:
            return

        cats = config.SESSION_LOG_CATEGORIES
        if cats != "ALL" and category not in cats:
            return

        entry = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "cat": category,
            **data,
        }
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with self._lock:
            self._file.write(line + "\n")
            self._file.flush()

            if category == "ERROR" or data.get("action") == "error":
                sys.stderr.write(f"{_RED}{line}{_RESET}\n")
                sys.stderr.flush()


glog = GameLogger()
