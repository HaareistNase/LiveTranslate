import re
import time
from dataclasses import dataclass
from typing import Any

from config import ASR_MIN_TEXT_CHARACTERS
from hallucination_filter import (
    is_known_hallucination,
    normalize_text,
)


_WORD_PATTERN = re.compile(
    r"\S+",
    re.UNICODE
)


@dataclass
class ActiveLine:
    speaker: str
    start: str
    text: str
    emitted_words: int
    last_update: float


class TranscriptAssembler:
    """
    Gibt bei wachsenden Whisper-Zeilen nur stabile Wörter frei.

    Das jeweils letzte Wort bleibt zunächst zurück, weil Whisper es
    noch verlängern oder korrigieren kann. So entstehen keine Fragmente
    wie "Анд рей", "рус ский" oder "Ж ив у".
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.active_lines: dict[
            tuple[str, str],
            ActiveLine
        ] = {}
        self.last_active_key: (
            tuple[str, str] | None
        ) = None

    def _log(self, stage: str, value) -> None:
        if self.logger is not None:
            self.logger.log(stage, value)

    @staticmethod
    def _line_key(
        item: dict[str, Any]
    ) -> tuple[str, str] | None:
        start = item.get("start")

        if start is None:
            return None

        speaker = str(
            item.get("speaker", "")
        )

        return speaker, str(start)

    @staticmethod
    def _words(text: str) -> list[str]:
        return _WORD_PATTERN.findall(
            normalize_text(text)
        )

    def _emit_stable_words(
        self,
        line: ActiveLine
    ) -> str:
        words = self._words(line.text)

        stable_word_count = max(
            0,
            len(words) - 1
        )

        if stable_word_count <= line.emitted_words:
            return ""

        new_words = words[
            line.emitted_words:
            stable_word_count
        ]

        line.emitted_words = stable_word_count

        return " ".join(new_words).strip()

    def _finalize_line(
        self,
        key: tuple[str, str]
    ) -> str:
        line = self.active_lines.pop(
            key,
            None
        )

        if line is None:
            return ""

        words = self._words(line.text)

        remaining = " ".join(
            words[line.emitted_words:]
        ).strip()

        self._log(
            "ASSEMBLER_FINALIZE",
            {
                "key": key,
                "remaining": remaining,
                "full_text": line.text,
            }
        )

        return remaining

    def add_item(
        self,
        item: dict[str, Any]
    ) -> str:
        text = normalize_text(
            item.get("text")
        )

        self._log(
            "ASSEMBLER_RAW_ITEM",
            {
                "speaker": item.get("speaker"),
                "start": item.get("start"),
                "end": item.get("end"),
                "text": text,
            }
        )

        if (
            len(text) < ASR_MIN_TEXT_CHARACTERS
            or is_known_hallucination(text)
        ):
            return ""

        key = self._line_key(item)

        if key is None:
            return text

        output_parts = []

        if (
            self.last_active_key is not None
            and key != self.last_active_key
        ):
            remaining = self._finalize_line(
                self.last_active_key
            )

            if remaining:
                output_parts.append(remaining)

        now = time.monotonic()
        line = self.active_lines.get(key)

        if line is None:
            line = ActiveLine(
                speaker=key[0],
                start=key[1],
                text=text,
                emitted_words=0,
                last_update=now
            )
            self.active_lines[key] = line
        else:
            line.text = text
            line.last_update = now
            line.emitted_words = min(
                line.emitted_words,
                len(self._words(text))
            )

        self.last_active_key = key

        stable = self._emit_stable_words(line)

        if stable:
            output_parts.append(stable)

        output = " ".join(
            part
            for part in output_parts
            if part
        ).strip()

        self._log(
            "ASSEMBLER_OUTPUT",
            {
                "key": key,
                "current": text,
                "emitted_words": line.emitted_words,
                "new_text": output,
            }
        )

        return output

    def flush_stale(
        self,
        maximum_age_seconds: float = 1.2
    ) -> str:
        if self.last_active_key is None:
            return ""

        line = self.active_lines.get(
            self.last_active_key
        )

        if line is None:
            return ""

        if (
            time.monotonic() - line.last_update
            < maximum_age_seconds
        ):
            return ""

        remaining = self._finalize_line(
            self.last_active_key
        )

        self.last_active_key = None
        return remaining

    def flush_all(self) -> str:
        parts = []

        for key in list(
            self.active_lines.keys()
        ):
            remaining = self._finalize_line(key)

            if remaining:
                parts.append(remaining)

        self.last_active_key = None

        return " ".join(parts).strip()
