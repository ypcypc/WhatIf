from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from core.llm import LLMClient
from core.models import EventData, SentenceData
import config


def _get_text(sentences: SentenceData, sentence_range: list[int]) -> str:
    start, end = sentence_range
    return "".join(s.text for s in sentences.sentences if start <= s.index <= end)


class DecisionTextExtractor:

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self._config = config.get_llm_config("decision_text_extractor")
        self._template = self._load_prompt()

    def _load_prompt(self) -> str:
        path = Path(__file__).parent / "prompts" / "decision_text_extraction.txt"
        return path.read_text(encoding="utf-8")

    def compress(self, original_text: str) -> str:
        n = len(original_text)
        char_min = int(n * 0.3)
        char_max = int(n * 0.4)
        prompt = (
            self._template
            .replace("{original_text}", original_text)
            .replace("{char_min}", str(char_min))
            .replace("{char_max}", str(char_max))
        )
        return self.llm.generate(
            prompt=prompt,
            model=self._config.model,
            temperature=self._config.temperature,
            thinking_budget=self._config.thinking_budget,
            extra_params=self._config.extra_params or None,
            api_base=self._config.api_base,
            api_key_env=self._config.api_key_env,
            log=False,
        )

    def extract_all(
        self, events: EventData, sentences: SentenceData, max_workers: int = 4,
    ) -> None:
        units: list[tuple[str, object, str | None]] = []
        for event in events.events:
            if event.type == "interactive" and event.phases:
                for phase_name, phase in event.phases.items():
                    if phase.sentence_range:
                        text = _get_text(sentences, phase.sentence_range)
                        units.append((text, event, phase_name))
            else:
                text = _get_text(sentences, event.sentence_range)
                units.append((text, event, None))

        print(f"  [DecisionTextExtractor] 并发提取 {len(units)} 个文本单元...")

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self.compress, text): (event, phase_name)
                for text, event, phase_name in units
            }
            for future in as_completed(futures):
                event, phase_name = futures[future]
                dt = future.result()
                if phase_name:
                    event.phases[phase_name].decision_text = dt
                else:
                    event.decision_text = dt
                label = f"{event.id}/{phase_name}" if phase_name else event.id
                print(f"    + {label} ({len(dt)} chars)")
