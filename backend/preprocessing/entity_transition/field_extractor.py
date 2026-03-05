import json

from core.models import EventData, LorebookData


def extract_events_for_stage3(events: EventData) -> str:
    slim = [
        {
            "id": e.id,
            "type": e.type,
            "decision_text": e.decision_text,
            "goal": e.goal,
            "sentence_range": e.sentence_range,
        }
        for e in events.events
    ]
    return json.dumps(slim, ensure_ascii=False, indent=2)


def extract_characters_for_stage3(lorebook: LorebookData) -> list[dict]:
    return [
        {
            "id": c.id,
            "name": c.name,
            "aliases": c.aliases,
            "importance": c.importance.value,
            "role": c.identity.role,
            "affiliation": c.identity.affiliation,
        }
        for c in lorebook.characters
    ]


def extract_locations_for_stage3(lorebook: LorebookData) -> list[dict]:
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "aliases": loc.aliases,
            "importance": loc.importance.value,
            "type": loc.type.value,
            "parent_location": loc.parent_location,
            "overview": loc.description.overview,
        }
        for loc in lorebook.locations
    ]


def extract_items_for_stage3(lorebook: LorebookData) -> list[dict]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "aliases": item.aliases,
            "importance": item.importance.value,
            "category": item.category.value,
            "primary_use": item.function.primary_use if item.function else "",
        }
        for item in lorebook.items
    ]


def extract_knowledge_for_stage3(lorebook: LorebookData) -> list[dict]:
    return [
        {
            "id": k.id,
            "name": k.name,
            "initial_holders": k.initial_holders,
            "description": k.description,
        }
        for k in lorebook.knowledge
    ]


def build_stage3_registry(lorebook: LorebookData) -> dict:
    return {
        "characters": extract_characters_for_stage3(lorebook),
        "locations": extract_locations_for_stage3(lorebook),
        "items": extract_items_for_stage3(lorebook),
        "knowledge": extract_knowledge_for_stage3(lorebook),
    }
