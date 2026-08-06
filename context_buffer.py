import re
import time
from collections import deque

from config import (
    CONTEXT_FLUSH_SECONDS,
    CONTEXT_MAX_CHARACTERS,
    CONTEXT_MAX_SENTENCES,
    CONTEXT_MAX_WAIT_SECONDS,
)
from hallucination_filter import (
    is_known_hallucination,
    normalize_text,
    strip_known_hallucinations,
)


_SENTENCE_END = re.compile(
    r"(?<=[.!?。！？…])\s+"
)


class ContextBuffer:
    """
    Sammelt neue Whisper-Textteile zu übersetzbaren Blöcken.

    Ein Block wird ausgegeben, wenn:
    - genügend vollständige Sätze vorliegen,
    - die gesamte Textmenge die Zeichengrenze erreicht,
    - eine Sprechpause erkannt wurde,
    - oder der Block trotz durchgehender Sprache zu lange offen ist.
    """

    def __init__(
        self,
        logger=None
    ):
        self.logger = logger
        self.partial = ""
        self.sentences = deque()

        self.last_update = None
        self.block_started = None

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

    def _extract_sentences(self) -> None:
        text = normalize_text(
            self.partial
        )

        if not text:
            return

        parts = _SENTENCE_END.split(
            text
        )

        if len(parts) == 1:
            return

        for part in parts[:-1]:
            part = part.strip()

            if part:
                self.sentences.append(
                    part
                )

        self.partial = parts[-1].strip()

    def _total_characters(self) -> int:
        sentence_chars = sum(
            len(sentence)
            for sentence in self.sentences
        )

        separators = max(
            0,
            len(self.sentences) - 1
        )

        if self.partial:
            separators += (
                1
                if self.sentences
                else 0
            )

        return (
            sentence_chars
            + len(self.partial)
            + separators
        )

    def _build_one_block(self) -> str:
        selected = []
        length = 0

        while self.sentences:
            next_sentence = (
                self.sentences[0]
            )

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

        # Bei durchgehender Sprache kann lange kein Satzzeichen kommen.
        # Dann wird auch der unvollständige Rest als Block ausgegeben.
        if (
            not selected
            and self.partial
        ):
            selected.append(
                self.partial
            )

            self.partial = ""

        block = " ".join(
            selected
        ).strip()

        return block

    def _flush_available(
        self,
        force_all: bool
    ) -> list[str]:
        blocks = []

        while self.sentences:
            block = self._build_one_block()

            if block:
                blocks.append(
                    block
                )

            if not force_all:
                break

        if (
            force_all
            and self.partial
        ):
            partial = self.partial.strip()
            self.partial = ""

            if partial:
                blocks.append(
                    partial
                )

        if (
            not self.sentences
            and not self.partial
        ):
            self.block_started = None
            self.last_update = None

        return blocks

    def add_confirmed(
        self,
        confirmed_text: str
    ) -> list[str]:
        confirmed_text = strip_known_hallucinations(
            confirmed_text
        )

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

        now = time.monotonic()

        if self.block_started is None:
            self.block_started = now

        self.last_update = now

        self._log(
            "CONTEXT_INPUT",
            confirmed_text
        )

        self.partial = normalize_text(
            f"{self.partial} {confirmed_text}"
        )

        self._extract_sentences()

        self._log(
            "CONTEXT_PARTIAL",
            self.partial
        )

        block_age = (
            now - self.block_started
            if self.block_started is not None
            else 0.0
        )

        must_flush = (
            len(self.sentences)
            >= CONTEXT_MAX_SENTENCES
            or self._total_characters()
            >= CONTEXT_MAX_CHARACTERS
            or block_age
            >= CONTEXT_MAX_WAIT_SECONDS
        )

        if not must_flush:
            return []

        blocks = self._flush_available(
            force_all=True
        )

        self._log(
            "CONTEXT_BLOCKS",
            blocks
        )

        return blocks

    def flush_if_old(
        self
    ) -> list[str]:
        if (
            self.last_update is None
            or (
                not self.sentences
                and not self.partial
            )
        ):
            return []

        now = time.monotonic()

        silent_long_enough = (
            now - self.last_update
            >= CONTEXT_FLUSH_SECONDS
        )

        open_too_long = (
            self.block_started is not None
            and now - self.block_started
            >= CONTEXT_MAX_WAIT_SECONDS
        )

        if (
            not silent_long_enough
            and not open_too_long
        ):
            return []

        blocks = self._flush_available(
            force_all=True
        )

        self._log(
            "CONTEXT_FLUSH",
            blocks
        )

        return blocks

    def flush_all(
        self
    ) -> list[str]:
        blocks = self._flush_available(
            force_all=True
        )

        self._log(
            "CONTEXT_FINAL_FLUSH",
            blocks
        )

        return blocks
