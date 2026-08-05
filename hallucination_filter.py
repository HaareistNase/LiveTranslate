import re
from typing import Any


PATTERNS = (
    r"dima\s*torzok",
    r"dimatorzok",
    r"субтитры\s+сделал",
    r"субтитры\s+подготовил",
    r"автор\s+субтитров",
    r"subtitles?\s+by",
    r"untertitel\s+(von|erstellt|gemacht)",
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    return " ".join(value.split()).strip()


def is_known_hallucination(value: Any) -> bool:
    text = normalize_text(value).lower()

    if not text:
        return False

    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in PATTERNS
    )
