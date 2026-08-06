import re
from typing import Any


_SENTENCE_SPLIT = re.compile(
    r"(?<=[.!?…])\s+"
)


class SubtitlePostprocessor:
    """
    Vorsichtige Nachbearbeitung direkt nach NLLB.

    Die Klasse übersetzt nichts neu. Sie bereinigt nur Formatierung,
    entfernt direkt benachbarte Satzdopplungen und hält extrem kurze
    Fragmente bis zum nächsten Übersetzungsblock zurück.
    """

    def __init__(
        self,
        short_fragment_words: int = 2,
        short_fragment_characters: int = 18
    ):
        self.short_fragment_words = (
            short_fragment_words
        )

        self.short_fragment_characters = (
            short_fragment_characters
        )

        self.pending_fragment = ""

    @staticmethod
    def normalize(
        value: Any
    ) -> str:
        if value is None:
            return ""

        text = " ".join(
            str(value).split()
        ).strip()

        if not text:
            return ""

        # Leerzeichen vor Satzzeichen entfernen.
        text = re.sub(
            r"\s+([,.;:!?])",
            r"\1",
            text
        )

        # Nach Satzzeichen genau ein Leerzeichen, sofern Text folgt.
        text = re.sub(
            r"([,.;:!?])(?=[^\s.,;:!?])",
            r"\1 ",
            text
        )

        # Mehrfachpunkte und übermäßige Satzzeichen beruhigen.
        text = re.sub(
            r"\.{4,}",
            "...",
            text
        )

        text = re.sub(
            r"([!?])\1{2,}",
            r"\1",
            text
        )

        return " ".join(
            text.split()
        ).strip()

    @staticmethod
    def _sentence_key(
        sentence: str
    ) -> str:
        return re.sub(
            r"[^\wäöüß]+",
            " ",
            sentence.casefold()
        ).strip()

    def remove_adjacent_duplicates(
        self,
        text: str
    ) -> str:
        parts = [
            part.strip()
            for part in _SENTENCE_SPLIT.split(
                text
            )
            if part.strip()
        ]

        if len(parts) < 2:
            return text

        result = []
        previous_key = ""

        for part in parts:
            key = self._sentence_key(
                part
            )

            if (
                key
                and key == previous_key
            ):
                continue

            result.append(
                part
            )
            previous_key = key

        return " ".join(
            result
        ).strip()

    def is_short_fragment(
        self,
        text: str
    ) -> bool:
        words = text.split()

        if not words:
            return False

        # Vollständige kurze Aussagen wie "Danke." bleiben sichtbar.
        has_sentence_end = bool(
            re.search(
                r"[.!?…]$",
                text
            )
        )

        return (
            not has_sentence_end
            and (
                len(words)
                <= self.short_fragment_words
                or len(text)
                <= self.short_fragment_characters
            )
        )

    def process(
        self,
        translated_text: Any
    ) -> list[str]:
        text = self.normalize(
            translated_text
        )

        text = self.remove_adjacent_duplicates(
            text
        )

        if not text:
            return []

        if self.pending_fragment:
            text = self.normalize(
                f"{self.pending_fragment} {text}"
            )

            self.pending_fragment = ""

        if self.is_short_fragment(
            text
        ):
            self.pending_fragment = text
            return []

        return [
            text
        ]

    def flush(
        self
    ) -> list[str]:
        if not self.pending_fragment:
            return []

        text = self.pending_fragment
        self.pending_fragment = ""

        return [
            text
        ]
