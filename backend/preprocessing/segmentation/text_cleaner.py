import re


def clean_text(text: str) -> str:
    text = re.sub(r"第[一二三四五六七八九十百千万零\d]+章\s*[^\n]*\n?", "", text)
    text = re.sub(r"Chapter\s+\d+[^\n]*\n?", "", text, flags=re.IGNORECASE)

    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    text = text.strip()

    return text
