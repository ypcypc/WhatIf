from runtime.agents.models import L0Summary, L1Summary


def format_l0_summaries(l0s: list[L0Summary]) -> str:
    if not l0s:
        return "<empty/>"
    parts = []
    for l0 in l0s:
        parts.append(
            f'<l0 event_id="{l0.event_id}">\n'
            f'<summary>{l0.summary}</summary>\n'
            f'<tags>{", ".join(l0.tags)}</tags>\n'
            f'</l0>'
        )
    return "\n".join(parts)


def format_l1_summaries(l1s: list[L1Summary]) -> str:
    if not l1s:
        return "<empty/>"
    parts = []
    for l1 in l1s:
        parts.append(
            f'<l1 id="{l1.id}" covers="{l1.covers}">\n'
            f'<summary>{l1.summary}</summary>\n'
            f'<tags>{", ".join(l1.tags)}</tags>\n'
            f'</l1>'
        )
    return "\n".join(parts)
