_VALID_GRANULARITY = {"named", "functional"}
_VALID_TYPES = {"character", "item", "information", "location"}
_VALID_ATTRIBUTES = {"地点", "持有者", "知晓者"}
_TYPE_TO_ATTR = {
    "character": "地点",
    "item": "持有者",
    "information": "知晓者",
    "location": "地点",
}


def validate_necessity(necessity_data: dict, events_slim: list[dict]) -> list[str]:
    errors = []

    for event_entry in necessity_data.get("events", []):
        eid = event_entry.get("event_id", "?")
        ne = event_entry.get("necessary_entities", {})

        for category in ("characters", "items", "information", "locations"):
            for entity in ne.get(category, []):
                if not isinstance(entity, dict):
                    errors.append(
                        f"{eid}: 必要实体应为 dict 格式，实际为 {type(entity).__name__}"
                    )
                    continue
                g = entity.get("granularity")
                if g not in _VALID_GRANULARITY:
                    errors.append(
                        f"{eid}: '{entity.get('name', '?')}' 的 granularity "
                        f"'{g}' 不合法，必须是 named 或 functional"
                    )

    return errors


def validate_transitions(
    transitions: list[dict],
    registry: dict,
) -> list[str]:
    errors = []

    valid_names = {"null"}
    for category in ("characters", "locations", "items", "knowledge"):
        for entity in registry.get(category, []):
            valid_names.add(entity["name"])
            for alias in entity.get("aliases", []):
                if alias:
                    valid_names.add(alias)

    for event in transitions:
        eid = event.get("event_id", "?")

        for entry in event.get("preconditions", []):
            _validate_entry(entry, eid, valid_names, errors)
            if "to" in entry:
                errors.append(
                    f"{eid}: precondition '{entry.get('name', '')}' 不应有 'to' 字段"
                )

        for entry in event.get("effects", []):
            _validate_entry(entry, eid, valid_names, errors)
            if entry.get("to") is None:
                errors.append(
                    f"{eid}: effect '{entry.get('name', '')}' 缺少 'to' 字段"
                )

    return errors


def _validate_entry(
    entry: dict, eid: str, valid_names: set[str], errors: list[str]
) -> None:
    name = entry.get("name", "")
    etype = entry.get("type", "")
    attr = entry.get("attribute", "")

    if etype not in _VALID_TYPES:
        errors.append(f"{eid}: 非法 type '{etype}'")

    if attr not in _VALID_ATTRIBUTES:
        errors.append(f"{eid}: 非法 attribute '{attr}'")

    expected = _TYPE_TO_ATTR.get(etype)
    if expected and attr != expected:
        errors.append(
            f"{eid}: {name} type='{etype}' 应搭配 attribute='{expected}'，"
            f"实际为 '{attr}'"
        )

    for field in ("from", "to"):
        value = entry.get(field)
        if value is not None and value != "null" and value not in valid_names:
            errors.append(f"{eid}: {name} 的 {field} '{value}' 不在注册表中")

    if entry.get("granularity") not in _VALID_GRANULARITY:
        errors.append(f"{eid}: {name} granularity 不合法")
