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


def _word_key(word: str) -> str:
    return word.casefold().strip()


def _common_prefix_words(
    left: list[str],
    right: list[str]
) -> int:
    count = 0

    for left_word, right_word in zip(
        left,
        right
    ):
        if (
            _word_key(left_word)
            != _word_key(right_word)
        ):
            break

        count += 1

    return count


@dataclass
class TrackedLine:
    key: tuple[str, str]
    current_text: str
    committed_text: str
    created_at: float
    updated_at: float
    last_commit_at: float


class TranscriptAssembler:
    """
    Präfix-basierter Tracker für sehr lange WhisperLiveKit-Zeilen.

    WhisperLiveKit kann dieselbe Startzeit über viele Sekunden oder
    sogar länger als eine Minute weiterführen. Eine Zwischenfreigabe
    darf die Zeile deshalb nicht löschen.

    Für jede Zeile bleiben erhalten:

    - current_text: neuester vollständiger Whisper-Stand
    - committed_text: bereits an den ContextBuffer ausgegebener Stand

    Bei einer weiteren Aktualisierung wird nur der Wort-Suffix hinter
    dem gemeinsamen Präfix ausgegeben.
    """

    def __init__(
        self,
        logger=None
    ):
        self.logger = logger

        self.lines: dict[
            tuple[str, str],
            TrackedLine
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
    def _suffix_after_committed(
        committed_text: str,
        current_text: str
    ) -> str:
        committed_text = normalize_text(
            committed_text
        )

        current_text = normalize_text(
            current_text
        )

        if not current_text:
            return ""

        if not committed_text:
            return current_text

        if current_text == committed_text:
            return ""

        committed_words = (
            committed_text.split()
        )

        current_words = (
            current_text.split()
        )

        prefix_length = (
            _common_prefix_words(
                committed_words,
                current_words
            )
        )

        # Normalfall: Der bereits ausgegebene Text ist weiterhin
        # vollständig am Anfang der wachsenden Zeile enthalten.
        if prefix_length == len(
            committed_words
        ):
            return " ".join(
                current_words[
                    prefix_length:
                ]
            ).strip()

        # Whisper hat einen früheren Teil korrigiert. Bereits ausgegebene
        # Wörter werden nicht erneut gesendet. Nur Wörter hinter dem
        # bisherigen Präfixumfang dürfen neu erscheinen.
        if (
            prefix_length
            >= max(
                1,
                len(committed_words) - 3
            )
            and len(current_words)
            > len(committed_words)
        ):
            return " ".join(
                current_words[
                    len(committed_words):
                ]
            ).strip()

        # Starke Rückkorrektur oder Neustart derselben Startzeit:
        # nichts doppelt ausgeben. Der aktuelle Stand bleibt gespeichert
        # und kann bei späterem Wachstum wieder sauber anschließen.
        return ""

    def _commit(
        self,
        key: tuple[str, str],
        remove_line: bool
    ) -> str:
        line = self.lines.get(
            key
        )

        if line is None:
            return ""

        output = (
            self._suffix_after_committed(
                line.committed_text,
                line.current_text
            )
        )

        # Entscheidend: Selbst nach einer Zwischenfreigabe bleibt der
        # ausgegebene Präfix gespeichert.
        line.committed_text = (
            line.current_text
        )

        line.last_commit_at = (
            time.monotonic()
        )

        self._log(
            "PREFIX_TRACKER_COMMIT",
            {
                "key": key,
                "current_text": (
                    line.current_text
                ),
                "committed_text": (
                    line.committed_text
                ),
                "output": output,
                "remove_line": remove_line,
            }
        )

        if remove_line:
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
            "PREFIX_TRACKER_UPDATE",
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

        outputs = []
        now = time.monotonic()

        # Eine wirklich neue Startzeit schließt die vorherige Zeile ab.
        # Nur dann wird deren Zustand entfernt.
        if (
            self.active_key is not None
            and key != self.active_key
        ):
            previous_output = self._commit(
                self.active_key,
                remove_line=True
            )

            if previous_output:
                outputs.append(
                    previous_output
                )

        line = self.lines.get(
            key
        )

        if line is None:
            line = TrackedLine(
                key=key,
                current_text=text,
                committed_text="",
                created_at=now,
                updated_at=now,
                last_commit_at=now
            )

            self.lines[key] = line

        else:
            line.current_text = text
            line.updated_at = now

        self.active_key = key

        # Eine extrem lange WLK-Zeile wird regelmäßig teilweise
        # freigegeben. Anders als früher bleibt die Zeile danach erhalten.
        if (
            now - line.last_commit_at
            >= ASR_LINE_MAX_SECONDS
        ):
            periodic_output = self._commit(
                key,
                remove_line=False
            )

            if periodic_output:
                outputs.append(
                    periodic_output
                )

        return " ".join(
            part
            for part in outputs
            if part
        ).strip()

    def flush_stale(
        self,
        maximum_age_seconds: float | None = None
    ) -> str:
        """
        Gibt den aktuellen neuen Suffix nach einer Pause frei, behält
        die Zeile aber samt committed_text für spätere Erweiterungen.
        """
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
            remove_line=False
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
                remove_line=True
            )

            if output:
                outputs.append(
                    output
                )

        self.active_key = None

        return " ".join(
            outputs
        ).strip()
