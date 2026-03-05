import json
from pathlib import Path
from typing import Any

import config


class LorebookQuery:

    def __init__(self, lorebook_dir: Path | None = None):
        self.lorebook_dir = lorebook_dir or (config.OUTPUT_BASE / "lorebook")
        self._index: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        characters_file = self.lorebook_dir / "characters.json"
        if characters_file.exists():
            data = json.loads(characters_file.read_text(encoding="utf-8"))
            for char in data.get("characters", []):
                self._index[char["id"]] = {"type": "character", "data": char}

        locations_file = self.lorebook_dir / "locations.json"
        if locations_file.exists():
            data = json.loads(locations_file.read_text(encoding="utf-8"))
            for loc in data.get("locations", []):
                self._index[loc["id"]] = {"type": "location", "data": loc}

        items_file = self.lorebook_dir / "items.json"
        if items_file.exists():
            data = json.loads(items_file.read_text(encoding="utf-8"))
            for item in data.get("items", []):
                self._index[item["id"]] = {"type": "item", "data": item}

    def get(self, entity_id: str) -> dict[str, Any] | None:
        entry = self._index.get(entity_id)
        if entry is None:
            return None
        return {"id": entity_id, "type": entry["type"], "data": entry["data"]}

    def get_many(self, entity_ids: list[str]) -> list[dict[str, Any]]:
        results = []
        for eid in entity_ids:
            entity = self.get(eid)
            if entity is not None:
                results.append(entity)
        return results

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._index

    def all_ids(self) -> list[str]:
        return list(self._index.keys())

    def to_lorebook_content(self) -> str:
        lorebook_data = {
            "characters": {"characters": [e["data"] for e in self._index.values() if e["type"] == "character"]},
            "locations": {"locations": [e["data"] for e in self._index.values() if e["type"] == "location"]},
            "items": {"items": [e["data"] for e in self._index.values() if e["type"] == "item"]},
        }
        return json.dumps(lorebook_data, ensure_ascii=False)

    def __len__(self) -> int:
        return len(self._index)
