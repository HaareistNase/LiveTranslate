import re
import time
from collections import deque

from config import (
    CONTEXT_FLUSH_SECONDS,
    CONTEXT_MAX_CHARACTERS,
    CONTEXT_MAX_SENTENCES,
)
from hallucination_filter import (
    is_known_hallucination,
    normalize_text,
)


_SENTENCE_END = re.compile(
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


class ContextBuffer:
    """
    Sammelt bestätigten Whisper-Text zu kleinen Kontextblöcken.

    Es gibt keine laufenden Vorschauen und keine Revisionen.
    Dadurch bleibt die aus v14 bekannte, stabile GUI-Logik erhalten.
    """

    def __init__(self):
        self.last_confirmed = ""
        self.partial = ""
        self.sentences = deque()
        self.last_update = None

    def _extract_sentences(self) -> None:
        text = normalize_text(self.partial)

        if not text:
            return

        parts = _SENTENCE_END.split(text)

        if len(parts) == 1:
            return

        for part in parts[:-1]:
            part = part.strip()

            if part:
                self.sentences.append(part)

        self.partial = parts[-1].strip()

    def _build_blocks(
        self,
        force: bool
    ) -> list[str]:
        blocks = []

        while self.sentences:
            selected = []
            length = 0

            while self.sentences:
                next_sentence = self.sentences[0]
                projected = (
                    length
                    + len(next_sentence)
                    + (1 if selected else 0)
                )

                if (
                    selected
                    and (
                        len(selected)
                        >= CONTEXT_MAX_SENTENCES
                        or projected
                        > CONTEXT_MAX_CHARACTERS
                    )
                ):
                    break

                selected.append(
                    self.sentences.popleft()
                )
                length = projected

                if (
                    len(selected)
                    >= CONTEXT_MAX_SENTENCES
                    or length
                    >= CONTEXT_MAX_CHARACTERS
                ):
                    break

            block = " ".join(selected).strip()

            if block:
                blocks.append(block)

            if not force:
                break

        return blocks

    def add_confirmed(
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
            self.last_confirmed,
            confirmed_text
        )

        self.last_confirmed = confirmed_text

        if not new_text:
            return []

        self.partial = normalize_text(
            f"{self.partial} {new_text}"
        )

        self.last_update = time.monotonic()

        self._extract_sentences()

        total_chars = sum(
            len(sentence)
            for sentence in self.sentences
        )

        if (
            len(self.sentences)
            >= CONTEXT_MAX_SENTENCES
            or total_chars
            >= CONTEXT_MAX_CHARACTERS
        ):
            return self._build_blocks(
                force=False
            )

        return []

    def flush_if_old(
        self
    ) -> list[str]:
        if self.last_update is None:
            return []

        if (
            time.monotonic() - self.last_update
            < CONTEXT_FLUSH_SECONDS
        ):
            return []

        if self.partial:
            self.sentences.append(
                self.partial
            )
            self.partial = ""

        self.last_update = None

        return self._build_blocks(
            force=True
        )

    def flush_all(
        self
    ) -> list[str]:
        if self.partial:
            self.sentences.append(
                self.partial
            )
            self.partial = ""

        self.last_update = None

        return self._build_blocks(
            force=True
        )
