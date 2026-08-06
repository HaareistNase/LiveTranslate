import re
from collections import Counter
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

# Typische Whisper-Halluzination in russischen Videos.
CONTINUED_PATTERN = re.compile(
    r"(?:п[\W_]*р[\W_]*о[\W_]*д[\W_]*о[\W_]*л[\W_]*ж"
    r"[\W_]*е[\W_]*н[\W_]*и[\W_]*е\s+"
    r"с[\W_]*л[\W_]*е[\W_]*д[\W_]*у[\W_]*е[\W_]*т)"
    r"(?:[\s.!?…]*)",
    flags=re.IGNORECASE,
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    return " ".join(value.split()).strip()


def strip_known_hallucinations(
    value: Any
) -> str:
    """
    Entfernt bekannte Halluzinationsphrasen, behält aber echten Text
    davor und danach.

    Beispiel:
        "Живем Продолжение следует... Чего и вам желаем."
    wird zu:
        "Живем Чего и вам желаем."
    """
    text = normalize_text(value)

    if not text:
        return ""

    text = CONTINUED_PATTERN.sub(
        " ",
        text
    )

    # Mehrfach übrig gebliebene Satzzeichen und Leerzeichen bereinigen.
    text = re.sub(
        r"(?:\.\s*){2,}",
        ". ",
        text
    )

    text = re.sub(
        r"\s+([,.;:!?])",
        r"\1",
        text
    )

    return normalize_text(text)


def is_known_hallucination(value: Any) -> bool:
    original = normalize_text(value)
    text = original.lower()

    if not text:
        return False

    if any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
        for pattern in PATTERNS
    ):
        return True

    cleaned = strip_known_hallucinations(
        original
    )

    # Nur dann vollständig verwerfen, wenn nach dem Entfernen der
    # bekannten Phrase praktisch kein echter Inhalt mehr übrig bleibt.
    return (
        bool(
            CONTINUED_PATTERN.search(
                original
            )
        )
        and len(cleaned) < 8
    )


def _repeated_ngram_ratio(
    text: str,
    n: int = 2
) -> float:
    words = [
        word.casefold()
        for word in re.findall(
            r"\b[\w'-]+\b",
            text,
            flags=re.UNICODE
        )
    ]

    if len(words) < n * 3:
        return 0.0

    ngrams = [
        tuple(
            words[index:index + n]
        )
        for index in range(
            len(words) - n + 1
        )
    ]

    counts = Counter(ngrams)

    repeated = sum(
        count - 1
        for count in counts.values()
        if count > 1
    )

    return repeated / max(
        1,
        len(ngrams)
    )


def is_translation_explosion(
    source_text: Any,
    translated_text: Any
) -> bool:
    """
    Erkennt nur extreme, stark wiederholte Übersetzungsausgaben.

    Normale Längenunterschiede zwischen Sprachen werden ausdrücklich
    nicht gefiltert.
    """
    source = normalize_text(
        source_text
    )

    translated = normalize_text(
        translated_text
    )

    if not source or not translated:
        return False

    source_words = len(
        source.split()
    )

    translated_words = len(
        translated.split()
    )

    if translated_words < 18:
        return False

    length_ratio = (
        translated_words
        / max(
            1,
            source_words
        )
    )

    repeated_ratio = max(
        _repeated_ngram_ratio(
            translated,
            n=1
        ),
        _repeated_ngram_ratio(
            translated,
            n=2
        )
    )

    # Nur sehr deutliche Ausreißer verwerfen:
    # mindestens dreimal so viele Wörter UND starke Wiederholung.
    return (
        length_ratio >= 3.0
        and repeated_ratio >= 0.30
    )
