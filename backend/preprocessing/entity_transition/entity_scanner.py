from collections import defaultdict

from core.models import SentenceData


def scan_entities(
    events_slim: list[dict],
    registry: dict,
    sentences: SentenceData,
) -> dict[str, list[dict]]:
    sentence_map = {s.index: s.text for s in sentences.sentences}

    name_index: dict[str, list[dict]] = defaultdict(list)
    type_mapping = {
        "characters": "character",
        "locations": "location",
        "items": "item",
        "knowledge": "information",
    }

    for category, entity_type in type_mapping.items():
        for entity in registry.get(category, []):
            entry = {
                "id": entity["id"],
                "name": entity["name"],
                "type": entity_type,
            }
            name_index[entity["name"]].append(entry)
            for alias in entity.get("aliases", []):
                if alias and len(alias) >= 2:
                    name_index[alias].append(entry)

    results: dict[str, list[dict]] = {}

    for event in events_slim:
        eid = event["id"]
        sr = event["sentence_range"]
        if len(sr) != 2:
            continue

        event_text = ""
        for idx in range(sr[0], sr[1] + 1):
            if idx in sentence_map:
                event_text += sentence_map[idx]

        matched: dict[str, dict] = {}
        for name, entries in name_index.items():
            if name in event_text:
                for entry in entries:
                    if entry["id"] not in matched:
                        matched[entry["id"]] = {
                            "name": entry["name"],
                            "type": entry["type"],
                            "id": entry["id"],
                            "matched_text": name,
                        }

        results[eid] = list(matched.values())

    return results
