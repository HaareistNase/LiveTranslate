import re
import time
from collections import deque

from config import (
    SEGMENT_FLUSH_SECONDS,
    SEGMENT_MAX_CHARACTERS,
    SEGMENT_MAX_SENTENCES,
    SEGMENT_MIN_CHARACTERS,
)
from hallucination_filter import (
    is_known_hallucination,
    normalize_text,
)


SENTENCE_END_PATTERN = re.compile(
    r"(?<=[.!?。！？…])\s+"
)


def get_new_suffix(
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
        return current[len(previous):].strip()

    previous_words = previous.split()
    current_words = current.split()

    maximum_overlap = min(
        len(previous_words),
        len(current_words)
    )

    for overlap in range(
        maximum_overlap,
        0,
        -1
    ):
        if (
            previous_words[-overlap:]
            == current_words[:overlap]
        ):
            return " ".join(
                current_words[overlap:]
            ).strip()

    return current


def split_sentences(
    text: str
) -> tuple[list[str], str]:
    text = normalize_text(text)

    if not text:
        return [], ""

    parts = SENTENCE_END_PATTERN.split(
        text
    )

    complete = []

    for part in parts[:-1]:
        part = part.strip()

        if part:
            complete.append(part)

    remainder = parts[-1].strip()

    # Wenn der letzte Teil selbst mit Satzzeichen endet,
    # ist er ebenfalls vollständig.
    if remainder and re.search(
        r"[.!?。！？…]$",
        remainder
    ):
        complete.append(remainder)
        remainder = ""

    return complete, remainder


class ContextSegmenter:
    """
    Baut aus bestätigtem Streaming-Text sinnvolle Übersetzungsblöcke.

    Statt jedes Fragment einzeln zu übersetzen, werden bis zu drei
    zusammengehörige Sätze gemeinsam an NLLB geschickt. Dadurch erhält
    das Modell mehr lokalen Kontext und übersetzt Pronomen, Bezüge und
    Satzanschlüsse konsistenter.
    """

    def __init__(self):
        self.last_confirmed_text = ""
        self.partial_text = ""
        self.pending_sentences = deque()
        self.last_update_time = None

    def add_confirmed_text(
        self,
        confirmed_text: str
    ) -> list[str]:
        confirmed_text = normalize_text(
            confirmed_text
        )

        if (
            not confirmed_text
            or is_known_hallucination(
                confirmed_text
            )
        ):
            return []

        new_text = get_new_suffix(
            self.last_confirmed_text,
            confirmed_text
        )

        self.last_confirmed_text = confirmed_text

        if not new_text:
            return []

        self.partial_text = normalize_text(
            f"{self.partial_text} {new_text}"
        )

        self.last_update_time = time.monotonic()

        complete, self.partial_text = (
            split_sentences(
                self.partial_text
            )
        )

        for sentence in complete:
            if sentence:
                self.pending_sentences.append(
                    sentence
                )

        return self._build_ready_segments(
            force=False
        )

    def _build_ready_segments(
        self,
        force: bool
    ) -> list[str]:
        ready = []

        while self.pending_sentences:
            selected = []
            selected_length = 0

            while self.pending_sentences:
                next_sentence = (
                    self.pending_sentences[0]
                )

                projected_length = (
                    selected_length
                    + len(next_sentence)
                    + (1 if selected else 0)
                )

                if (
                    selected
                    and (
                        len(selected)
                        >= SEGMENT_MAX_SENTENCES
                        or projected_length
                        > SEGMENT_MAX_CHARACTERS
                    )
                ):
                    break

                selected.append(
                    self.pending_sentences.popleft()
                )

                selected_length = projected_length

                if (
                    len(selected)
                    >= SEGMENT_MAX_SENTENCES
                    or selected_length
                    >= SEGMENT_MAX_CHARACTERS
                ):
                    break

            if not selected:
                break

            segment = " ".join(
                selected
            ).strip()

            enough_content = (
                len(segment)
                >= SEGMENT_MIN_CHARACTERS
            )

            queue_has_more = bool(
                self.pending_sentences
            )

            if (
                force
                or enough_content
                or queue_has_more
            ):
                ready.append(segment)
            else:
                # Noch etwas Kontext sammeln.
                for sentence in reversed(selected):
                    self.pending_sentences.appendleft(
                        sentence
                    )
                break

        return ready

    def flush_if_old(self) -> list[str]:
        if self.last_update_time is None:
            return []

        age = (
            time.monotonic()
            - self.last_update_time
        )

        if age < SEGMENT_FLUSH_SECONDS:
            return []

        if self.partial_text:
            self.pending_sentences.append(
                self.partial_text
            )
            self.partial_text = ""

        self.last_update_time = None

        return self._build_ready_segments(
            force=True
        )

    def flush_all(self) -> list[str]:
        if self.partial_text:
            self.pending_sentences.append(
                self.partial_text
            )
            self.partial_text = ""

        self.last_update_time = None

        return self._build_ready_segments(
            force=True
        )
