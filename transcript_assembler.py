import re
from collections import deque
from difflib import SequenceMatcher
from typing import Any

from config import (
    ASR_DUPLICATE_SIMILARITY,
    ASR_FUZZY_WORD_SIMILARITY,
    ASR_MIN_TEXT_CHARACTERS,
    ASR_OVERLAP_MAX_WORDS,
    ASR_RECENT_LINE_CACHE,
)
from hallucination_filter import (
    is_known_hallucination,
    normalize_text,
)


_WORD_CLEANUP = re.compile(
    r"[^\w'-]+",
    re.UNICODE
)


def _word_key(word: str) -> str:
    return _WORD_CLEANUP.sub(
        "",
        word.casefold()
    )


def _text_key(text: str) -> str:
    return " ".join(
        token
        for token in (
            _word_key(word)
            for word in normalize_text(text).split()
        )
        if token
    )


def _similar(
    left: str,
    right: str,
    threshold: float
) -> bool:
    if left == right:
        return True

    if not left or not right:
        return False

    return (
        SequenceMatcher(
            None,
            left,
            right
        ).ratio()
        >= threshold
    )


def _words_match(
    left: str,
    right: str
) -> bool:
    left_key = _word_key(left)
    right_key = _word_key(right)

    if left_key == right_key:
        return True

    if (
        len(left_key) < 4
        or len(right_key) < 4
    ):
        return False

    return _similar(
        left_key,
        right_key,
        ASR_FUZZY_WORD_SIMILARITY
    )


def find_word_overlap(
    previous: str,
    current: str
) -> int:
    previous_words = normalize_text(
        previous
    ).split()

    current_words = normalize_text(
        current
    ).split()

    maximum = min(
        len(previous_words),
        len(current_words),
        ASR_OVERLAP_MAX_WORDS
    )

    for overlap in range(
        maximum,
        0,
        -1
    ):
        previous_tail = previous_words[
            -overlap:
        ]

        current_head = current_words[
            :overlap
        ]

        matches = sum(
            1
            for left, right in zip(
                previous_tail,
                current_head
            )
            if _words_match(
                left,
                right
            )
        )

        required = max(
            1,
            int(overlap * 0.82)
        )

        if matches >= required:
            return overlap

    return 0


def get_growth_suffix(
    previous: str,
    current: str
) -> str:
    previous = normalize_text(previous)
    current = normalize_text(current)

    if not current:
        return ""

    if not previous:
        return current

    if current == previous:
        return ""

    if current.startswith(previous):
        return current[
            len(previous):
        ].strip()

    if previous.startswith(current):
        return ""

    overlap = find_word_overlap(
        previous,
        current
    )

    if overlap:
        return " ".join(
            current.split()[overlap:]
        ).strip()

    return ""


class TranscriptAssembler:
    def __init__(
        self,
        logger=None
    ):
        self.logger = logger

        self.line_versions: dict[
            str,
            str
        ] = {}

        self.line_order = deque(
            maxlen=ASR_RECENT_LINE_CACHE
        )

        self.recent_completed_keys = deque(
            maxlen=ASR_RECENT_LINE_CACHE
        )

        self.last_unidentified_text = ""

    @staticmethod
    def _line_id(
        item: dict[str, Any]
    ) -> str:
        """
        WhisperLiveKit verlängert dieselbe laufende Zeile fortlaufend.
        Dabei bleibt der Startzeitpunkt gleich, während sich die Endzeit
        bei nahezu jedem Update verändert.

        Deshalb darf die Endzeit nicht Teil der Zeilen-ID sein.
        """
        start = item.get("start")
        speaker = item.get("speaker")

        if start is None:
            return ""

        return f"{speaker}|{start}"

    def _remember_line_version(
        self,
        line_id: str,
        text: str
    ) -> None:
        if line_id not in self.line_versions:
            self.line_order.append(
                line_id
            )

        self.line_versions[line_id] = text

        while (
            len(self.line_versions)
            > ASR_RECENT_LINE_CACHE
            and self.line_order
        ):
            oldest = self.line_order.popleft()

            self.line_versions.pop(
                oldest,
                None
            )

    def _is_completed_duplicate(
        self,
        text: str
    ) -> bool:
        key = _text_key(text)

        if not key:
            return True

        for old_key in self.recent_completed_keys:
            if _similar(
                key,
                old_key,
                ASR_DUPLICATE_SIMILARITY
            ):
                return True

        return False

    def _log_output(
        self,
        line_id: str,
        previous: str,
        current: str,
        new_text: str
    ) -> None:
        if self.logger is None:
            return

        self.logger.log(
            "ASSEMBLER_OUTPUT",
            {
                "line_id": line_id,
                "previous": previous,
                "current": current,
                "new_text": new_text,
            }
        )

    def add_item(
        self,
        item: dict[str, Any]
    ) -> str:
        text = normalize_text(
            item.get("text")
        )

        if self.logger is not None:
            self.logger.log(
                "ASSEMBLER_RAW_ITEM",
                {
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "text": text,
                }
            )

        if (
            len(text)
            < ASR_MIN_TEXT_CHARACTERS
            or is_known_hallucination(text)
        ):
            return ""

        line_id = self._line_id(
            item
        )

        if line_id:
            previous_version = (
                self.line_versions.get(
                    line_id,
                    ""
                )
            )

            new_text = get_growth_suffix(
                previous_version,
                text
            )

            self._remember_line_version(
                line_id,
                text
            )

            self._log_output(
                line_id,
                previous_version,
                text,
                new_text
            )

            return new_text

        previous = self.last_unidentified_text

        if not previous:
            new_text = text

        else:
            new_text = get_growth_suffix(
                previous,
                text
            )

            if (
                not new_text
                and not self._is_completed_duplicate(
                    text
                )
                and not _similar(
                    _text_key(previous),
                    _text_key(text),
                    ASR_DUPLICATE_SIMILARITY
                )
            ):
                new_text = text

        self.last_unidentified_text = text

        if new_text == text:
            key = _text_key(text)

            if key:
                self.recent_completed_keys.append(
                    key
                )

        self._log_output(
            "",
            previous,
            text,
            new_text
        )

        return new_text
