from typing import Type

from core.models import EventData, LorebookData
from preprocessing.base import ValidatedExtractor


class LorebookExtractor(ValidatedExtractor):

    @property
    def prompt_file(self) -> str:
        return "lorebook_extraction.txt"

    @property
    def response_model(self) -> Type[LorebookData]:
        return LorebookData

    def build_prompt(self, template: str, full_text: str, events: EventData) -> str:
        events_json = events.model_dump_json(indent=2)
        return (
            template
            .replace("{events_json}", events_json)
            .replace("{full_text}", full_text)
        )

    def validate(self, result: LorebookData, **kwargs) -> list[str]:
        errors = []

        char_ids = set()
        for c in result.characters:
            if c.id in char_ids:
                errors.append(f"角色 ID 重复: {c.id}")
            char_ids.add(c.id)
            if not c.name:
                errors.append(f"角色 {c.id}: 缺少 name")

        loc_ids = set()
        for loc in result.locations:
            if loc.id in loc_ids:
                errors.append(f"地点 ID 重复: {loc.id}")
            loc_ids.add(loc.id)

        item_ids = set()
        for item in result.items:
            if item.id in item_ids:
                errors.append(f"物品 ID 重复: {item.id}")
            item_ids.add(item.id)
            if item.function and not item.function.primary_use:
                errors.append(f"物品 {item.id}: function 存在但 primary_use 为空")

        for k in result.knowledge:
            if not k.initial_holders:
                errors.append(f"信息 {k.id}: 缺少 initial_holders")
            for holder in k.initial_holders:
                if holder not in char_ids:
                    errors.append(
                        f"信息 {k.id}: initial_holder '{holder}' 不在角色表中"
                    )

        all_ids = [c.id for c in result.characters]
        all_ids += [loc.id for loc in result.locations]
        all_ids += [item.id for item in result.items]
        all_ids += [k.id for k in result.knowledge]
        seen = set()
        for eid in all_ids:
            if eid in seen:
                errors.append(f"跨类型 ID 重复: {eid}")
            seen.add(eid)

        return errors
