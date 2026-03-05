import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Type

from pydantic import BaseModel

from core.llm import LLMClient
from core.models import (
    SentenceData,
    EventData,
    LorebookData,
    CharacterData,
    LocationData,
    ItemData,
    KnowledgeData,
    TransitionData,
    Metadata,
)
from preprocessing.segmentation import clean_text, split_sentences, EventExtractor
from preprocessing.segmentation.decision_text_extractor import DecisionTextExtractor
from preprocessing.lorebook import LorebookExtractor
from preprocessing.entity_transition import (
    scan_entities, build_stage3_registry,
    BatchManager, TokenEstimator, compute_fixed_costs,
)
from preprocessing.entity_transition.field_extractor import extract_events_for_stage3
from preprocessing.entity_transition.necessity_grader import NecessityGrader
from preprocessing.entity_transition.transition_annotator import TransitionAnnotator
from preprocessing.entity_transition.cross_validator import CrossValidator
from preprocessing.entity_transition.repairer import Repairer, merge_repairs
from preprocessing.entity_transition.validators import validate_transitions
import config


def load_json(path: Path, model: Type[BaseModel]) -> BaseModel:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def save_json(data: BaseModel | dict | list, path: Path, by_alias: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, BaseModel):
        text = data.model_dump_json(indent=2, by_alias=by_alias)
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


def run_step_if_needed(
    output_file: Path,
    step_func: Callable[[], Any],
    model: Type[BaseModel] | None = None,
) -> Any:
    if output_file.exists():
        print(f"  - 跳过（文件已存在）: {output_file.name}")
        if model:
            return load_json(output_file, model)
        return None
    result = step_func()
    return result


def _validate_decision_text(events: EventData) -> None:
    for event in events.events:
        if event.type == "interactive":
            if not event.phases:
                raise ValueError(f"Interactive event '{event.id}' missing phases")
            for phase_name, phase in event.phases.items():
                if not phase.decision_text:
                    raise ValueError(
                        f"Event '{event.id}' phase '{phase_name}' missing decision_text"
                    )
        elif event.type == "narrative":
            if not event.decision_text:
                raise ValueError(f"Narrative event '{event.id}' missing decision_text")


def _all_decision_texts_present(events: EventData) -> bool:
    for event in events.events:
        if event.type == "interactive":
            if not event.phases:
                return False
            if not all(phase.decision_text for phase in event.phases.values()):
                return False
        elif event.type == "narrative":
            if not event.decision_text:
                return False
    return True


def main(input_path: str, output_dir: str | None = None):
    input_file = Path(input_path)
    output_path = Path(output_dir) if output_dir else config.OUTPUT_BASE / input_file.stem

    if not input_file.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    print(f"[开始] 处理文件: {input_file.name}")
    print(f"[输出] 目录: {output_path}")
    print()

                                                                           
                                                                           
    print("=" * 50)
    print("[Stage 1] 事件切分")
    print("=" * 50)

    print("\n[Step 1.1] 文本预处理...")
    source_dir = output_path / "source"
    sentences_file = source_dir / "sentences.json"
    full_text_file = source_dir / "full_text.txt"

    if sentences_file.exists() and full_text_file.exists():
        print(f"  - 跳过（文件已存在）")
        clean = full_text_file.read_text(encoding="utf-8")
        sentences = load_json(sentences_file, SentenceData)
    else:
        raw_text = input_file.read_text(encoding="utf-8")
        clean = clean_text(raw_text)
        sentences = split_sentences(clean)

        source_dir.mkdir(parents=True, exist_ok=True)
        full_text_file.write_text(clean, encoding="utf-8")
        save_json(sentences, sentences_file)

    print(f"  - 总字符数: {sentences.total_characters}")
    print(f"  - 总句子数: {sentences.total_sentences}")

    llm = LLMClient()

    print("\n[Step 1.2] 事件结构提取...")
    events_dir = output_path / "events"
    events_file = events_dir / "events.json"

    events = run_step_if_needed(
        events_file,
        lambda: EventExtractor(llm).extract(sentences=sentences),
        EventData,
    )
    if not events_file.exists():
        save_json(events, events_file)
    print(f"  - 事件数量: {len(events.events)}")
    interactive_count = sum(1 for e in events.events if e.type == "interactive")
    narrative_count = sum(1 for e in events.events if e.type == "narrative")
    print(f"  - 交互型: {interactive_count}, 叙事型: {narrative_count}")

    print("\n[Step 1.3] Decision Text 提取...")
    if _all_decision_texts_present(events):
        print("  - 跳过（decision_text 已存在）")
    else:
        DecisionTextExtractor(llm).extract_all(events, sentences)
        _validate_decision_text(events)
        save_json(events, events_file)

                                                                           
                                                                           
    print("\n" + "=" * 50)
    print("[Stage 2] Lorebook（统一实体提取）")
    print("=" * 50)

    lorebook_dir = output_path / "lorebook"
    characters_file = lorebook_dir / "characters.json"
    locations_file = lorebook_dir / "locations.json"
    items_file = lorebook_dir / "items.json"
    knowledge_file = lorebook_dir / "knowledge.json"

    lorebook_marker = lorebook_dir / ".lorebook_done"

    lorebook_files = [characters_file, locations_file, items_file, knowledge_file]
    if lorebook_marker.exists() and all(f.exists() for f in lorebook_files):
        print("  - 跳过（文件已存在）")
        lorebook = LorebookData(
            characters=load_json(characters_file, CharacterData).characters,
            locations=load_json(locations_file, LocationData).locations,
            items=load_json(items_file, ItemData).items,
            knowledge=load_json(knowledge_file, KnowledgeData).knowledge,
        )
    else:
        lorebook = LorebookExtractor(llm).extract(full_text=clean, events=events)

        save_json(CharacterData(characters=lorebook.characters), characters_file)
        save_json(LocationData(locations=lorebook.locations), locations_file)
        save_json(ItemData(items=lorebook.items), items_file)
        save_json(KnowledgeData(knowledge=lorebook.knowledge), knowledge_file)
        lorebook_marker.parent.mkdir(parents=True, exist_ok=True)
        lorebook_marker.write_text("done", encoding="utf-8")

    print(f"  - 角色: {len(lorebook.characters)}")
    print(f"  - 地点: {len(lorebook.locations)}")
    print(f"  - 物品: {len(lorebook.items)}")
    print(f"  - 知识: {len(lorebook.knowledge)}")

                                                                           
                                                                           
    print("\n" + "=" * 50)
    print("[Stage 3] Entity Transition（实体状态变迁分析）")
    print("=" * 50)

    transitions_dir = output_path / "transitions"
    transitions_file = transitions_dir / "transitions.json"
    debug_dir = output_path / "debug"

    if transitions_file.exists():
        print("  - 跳过（文件已存在）")
        transitions = load_json(transitions_file, TransitionData)
    else:
        transitions = _run_stage3(
            llm, events, lorebook, sentences, debug_dir
        )
        save_json(transitions, transitions_file, by_alias=True)

    print(f"  - 转移事件数: {len(transitions.transitions)}")

                                                                           
              
                                                                           
    print("\n[Metadata] 生成元信息...")
    metadata_file = output_path / "metadata.json"

    metadata = Metadata(
        title=input_file.stem,
        source_file=str(input_file),
        total_characters=sentences.total_characters,
        total_sentences=sentences.total_sentences,
        event_count=len(events.events),
        character_count=len(lorebook.characters),
        location_count=len(lorebook.locations),
        item_count=len(lorebook.items),
        knowledge_count=len(lorebook.knowledge),
        transition_count=len(transitions.transitions),
        created_at=datetime.now().isoformat(),
    )
    save_json(metadata, metadata_file)
    print("  - 元信息已生成")

    print(f"\n[完成] WorldPkg 已生成到: {output_path}")


def _run_stage3(
    llm: LLMClient,
    events: EventData,
    lorebook: LorebookData,
    sentences: SentenceData,
    debug_dir: Path,
) -> TransitionData:

    events_json = extract_events_for_stage3(events)
    events_slim = json.loads(events_json)
    registry = build_stage3_registry(lorebook)

    print("\n[Step 3.1] 实体扫描...")
    candidates = scan_entities(events_slim, registry, sentences)
    save_json(candidates, debug_dir / "candidates.json")
    total_candidates = sum(len(v) for v in candidates.values())
    print(f"  - 候选实体匹配: {total_candidates} 次")

    estimator = TokenEstimator()
    fixed_costs = compute_fixed_costs(estimator)
    print(f"  - 固定开销 (tokens): {fixed_costs}")

    batch_mgr = BatchManager(estimator, fixed_costs)
    batches = batch_mgr.create_batches(events_slim, candidates, registry)
    print(f"\n  - 分为 {len(batches)} 个批次处理（token 预算驱动）")
    for i, bi in enumerate(batches):
        reg_size = sum(len(v) for v in bi.registry_subset.values())
        print(
            f"    批次 {i + 1}: {len(bi.events)} 事件, "
            f"{reg_size} registry 实体, overlap={bi.overlap_count}"
        )

    batch_results: list[list[dict]] = []

    for batch_idx, batch_info in enumerate(batches):
        print(
            f"\n--- 批次 {batch_idx + 1}/{len(batches)} "
            f"({len(batch_info.events)} 事件) ---"
        )

        batch_events_json = json.dumps(
            batch_info.events, ensure_ascii=False, indent=2
        )
        batch_candidates_json = json.dumps(
            batch_info.candidates_subset, ensure_ascii=False, indent=2
        )
        batch_registry_json = json.dumps(
            batch_info.registry_subset, ensure_ascii=False, indent=2
        )

                                           
        print("[Call 3.2] 必要性 + 颗粒度判断...")
        necessity = NecessityGrader(llm).extract(
            events_json=batch_events_json,
            candidates_json=batch_candidates_json,
            events_slim=batch_info.events,
        )
        if batch_idx == 0:
            save_json(necessity, debug_dir / "necessary.json")

        necessary_json = necessity.model_dump_json(indent=2)

        print("[Call 3.3] 转移标注...")
        transitions_draft = TransitionAnnotator(llm).extract(
            events_json=batch_events_json,
            necessary_json=necessary_json,
            registry_json=batch_registry_json,
            registry=registry,
        )
        draft_dicts = [
            {
                "event_id": t.event_id,
                "preconditions": [
                    p.model_dump(by_alias=True) for p in t.preconditions
                ],
                "effects": [
                    e.model_dump(by_alias=True) for e in t.effects
                ],
            }
            for t in transitions_draft.transitions
        ]
        if batch_idx == 0:
            save_json(draft_dicts, debug_dir / "transitions_draft.json")

        print("[Call 3.4] 交叉验证...")
        validation = CrossValidator(llm).extract(
            events_json=batch_events_json,
            transitions_draft=draft_dicts,
            events_slim=batch_info.events,
            registry_json=batch_registry_json,
            necessary_json=necessary_json,
        )
        if batch_idx == 0:
            save_json(validation, debug_dir / "validation_report.json")

        has_errors = any(r.errors for r in validation.reports)

        if has_errors:
            print("[Call 3.5] 发现错误，修复中...")
            error_eids = {r.event_id for r in validation.reports if r.errors}
            problematic = [e for e in draft_dicts if e["event_id"] in error_eids]
            error_reports = [
                r.model_dump() for r in validation.reports if r.errors
            ]

            repaired = Repairer(llm).extract(
                problematic_events=problematic,
                validation_reports=error_reports,
                registry_json=batch_registry_json,
            )
            final_dicts = merge_repairs(draft_dicts, repaired)
            if batch_idx == 0:
                save_json(final_dicts, debug_dir / "repairs.json")

            remaining_errors = validate_transitions(final_dicts, registry)
            if remaining_errors:
                print(f"  ⚠ 修复后仍有 {len(remaining_errors)} 个问题")
                for e in remaining_errors[:3]:
                    print(f"    · {e}")
        else:
            print("  - 验证通过，无需修复")
            final_dicts = draft_dicts

        batch_results.append(final_dicts)

    merged = batch_mgr.merge_results(batch_results, batches)

    final_errors = validate_transitions(merged, registry)
    if final_errors:
        print(f"\n  ⚠ 合并后全量验证发现 {len(final_errors)} 个问题")
        for e in final_errors[:5]:
            print(f"    · {e}")

    return TransitionData.model_validate({"transitions": merged})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract.py <input.txt> [output_dir]")
        print("示例: python extract.py ../data/novels/凡人修仙传.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        main(input_file, output)
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
