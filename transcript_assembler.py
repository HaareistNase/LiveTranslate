import time
from dataclasses import dataclass
from typing import Any

from config import (
    ASR_LINE_MAX_SECONDS,
    ASR_LINE_STALE_SECONDS,
    ASR_MIN_TEXT_CHARACTERS,
)
from hallucination_filter import (
    is_known_hallucination,
    normalize_text,
)


@dataclass
class LiveLine:
    key: tuple[str, str]
    text: str
    created_at: float
    updated_at: float
    committed_text: str = ""


def _common_prefix_word_count(
    previous: str,
    current: str
) -> int:
    previous_words = previous.split()
    current_words = current.split()

    count = 0

    for left, right in zip(
        previous_words,
        current_words
    ):
        if left.casefold() != right.casefold():
            break

        count += 1

    return count


class TranscriptAssembler:
    """
    Verwalter für wachsende WhisperLiveKit-Zeilen.

    Zwischenstände derselben Zeile ersetzen nur deren internen Stand.
    An den ContextBuffer geht erst eine abgeschlossene vollständige
    Zeile.
    """

    def __init__(
        self,
        logger=None
    ):
        self.logger = logger

        self.lines: dict[
            tuple[str, str],
            LiveLine
        ] = {}

        self.active_key: (
            tuple[str, str] | None
        ) = None

    def _log(
        self,
        stage: str,
        value
    ) -> None:
        if self.logger is not None:
            self.logger.log(
                stage,
                value
            )

    @staticmethod
    def _line_key(
        item: dict[str, Any]
    ) -> tuple[str, str] | None:
        start = item.get(
            "start"
        )

        if start is None:
            return None

        speaker = str(
            item.get(
                "speaker",
                ""
            )
        )

        return (
            speaker,
            str(start)
        )

    @staticmethod
    def _new_part(
        committed_text: str,
        final_text: str
    ) -> str:
        committed_text = normalize_text(
            committed_text
        )

        final_text = normalize_text(
            final_text
        )

        if not final_text:
            return ""

        if not committed_text:
            return final_text

        if final_text == committed_text:
            return ""

        if final_text.startswith(
            committed_text
        ):
            return final_text[
                len(committed_text):
            ].strip()

        prefix_words = (
            _common_prefix_word_count(
                committed_text,
                final_text
            )
        )

        final_words = final_text.split()

        if prefix_words:
            return " ".join(
                final_words[
                    prefix_words:
                ]
            ).strip()

        return ""

    def _commit(
        self,
        key: tuple[str, str],
        keep_line: bool
    ) -> str:
        line = self.lines.get(
            key
        )

        if line is None:
            return ""

        output = self._new_part(
            line.committed_text,
            line.text
        )

        line.committed_text = line.text

        self._log(
            "LIVELINE_COMMIT",
            {
                "key": key,
                "full_text": line.text,
                "output": output,
                "keep_line": keep_line,
            }
        )

        if not keep_line:
            self.lines.pop(
                key,
                None
            )

            if self.active_key == key:
                self.active_key = None

        return output

    def add_item(
        self,
        item: dict[str, Any]
    ) -> str:
        text = normalize_text(
            item.get(
                "text"
            )
        )

        self._log(
            "LIVELINE_UPDATE",
            {
                "speaker": item.get(
                    "speaker"
                ),
                "start": item.get(
                    "start"
                ),
                "end": item.get(
                    "end"
                ),
                "text": text,
            }
        )

        if (
            len(text)
            < ASR_MIN_TEXT_CHARACTERS
            or is_known_hallucination(
                text
            )
        ):
            return ""

        key = self._line_key(
            item
        )

        if key is None:
            return text

        output_parts = []

        if (
            self.active_key is not None
            and key != self.active_key
        ):
            previous_output = self._commit(
                self.active_key,
                keep_line=False
            )

            if previous_output:
                output_parts.append(
                    previous_output
                )

        now = time.monotonic()

        line = self.lines.get(
            key
        )

        if line is None:
            line = LiveLine(
                key=key,
                text=text,
                created_at=now,
                updated_at=now
            )

            self.lines[key] = line

        else:
            line.text = text
            line.updated_at = now

        self.active_key = key

        if (
            now - line.created_at
            >= ASR_LINE_MAX_SECONDS
        ):
            forced_output = self._commit(
                key,
                keep_line=True
            )

            line.created_at = now

            if forced_output:
                output_parts.append(
                    forced_output
                )

        return " ".join(
            output_parts
        ).strip()

    def flush_stale(
        self,
        maximum_age_seconds: float | None = None
    ) -> str:
        if self.active_key is None:
            return ""

        line = self.lines.get(
            self.active_key
        )

        if line is None:
            self.active_key = None
            return ""

        stale_seconds = (
            ASR_LINE_STALE_SECONDS
            if maximum_age_seconds is None
            else maximum_age_seconds
        )

        if (
            time.monotonic()
            - line.updated_at
            < stale_seconds
        ):
            return ""

        return self._commit(
            self.active_key,
            keep_line=False
        )

    def flush_all(
        self
    ) -> str:
        outputs = []

        for key in list(
            self.lines.keys()
        ):
            output = self._commit(
                key,
                keep_line=False
            )

            if output:
                outputs.append(
                    output
                )

        self.active_key = None

        return " ".join(
            outputs
        ).strip()
