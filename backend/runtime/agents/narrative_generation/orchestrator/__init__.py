import re
from pathlib import Path

from runtime.agents.narrative_generation.orchestrator.loop import (
    LoopConfig as LoopConfig,
    run_tool_loop as run_tool_loop,
)
from runtime.agents.narrative_generation.orchestrator.phase_config import PHASE_CONFIGS as PHASE_CONFIGS


def load_sections(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for m in re.finditer(r"--- (\w+) ---\n(.*?)(?=--- \w+ ---|\Z)", text, re.DOTALL):
        sections[m.group(1)] = m.group(2).strip()
    return sections
