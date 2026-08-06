import re
import time
from collections import deque

from config import (
    CONTEXT_FLUSH_SECONDS,
    CONTEXT_MAX_CHARACTERS,
    CONTEXT_MAX_SENTENCES,
    CONTEXT_MAX_WAIT_SECONDS,
    CONTEXT_MIN_SENTENCES,
    CONTEXT_TARGET_CHARACTERS,
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
    Baut aus bestätigten ASR-Teilen lesbare Übersetzungsblöcke.

    Kurze vollständige Sätze werden bevorzugt zusammengefasst.
    Ein Block wird ausgegeben, wenn:

    - die Zielgröße erreicht ist,
    - die harte Satz- oder Zeichengrenze erreicht ist,
    - eine Sprechpause vorliegt,
    - oder der Block zu lange offen ist.

    Ein unvollständiger Satz bleibt nach Möglichkeit im Puffer.
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

    def _extract_sentences(
        self
    ) -> None:
        text = normalize_text(
            self.partial
        )

        if not text:
            return

        parts = _SENTENCE_END.split(
            text
        )

        if len(parts) == 1:
            self.partial = text
            return

        for part in parts[:-1]:
            part = part.strip()

            if part:
                self.sentences.append(
                    part
                )

        self.partial = parts[-1].strip()

    @staticmethod
    def _joined_length(
        values: list[str]
    ) -> int:
        if not values:
            return 0

        return (
            sum(
                len(value)
                for value in values
            )
            + len(values)
            - 1
        )

    def _sentence_characters(
        self
    ) -> int:
        return self._joined_length(
            list(self.sentences)
        )

    def _total_characters(
        self
    ) -> int:
        values = list(
            self.sentences
        )

        if self.partial:
            values.append(
                self.partial
            )

        return self._joined_length(
            values
        )

    def _build_sentence_block(
        self,
        force: bool
    ) -> str:
        """
        Nimmt vollständige Sätze bis zur Ziel- bzw. Maximalgröße.

        Ohne force wird erst ausgegeben, wenn mindestens die Zielgröße
        oder eine harte Grenze erreicht ist.
        """
        if not self.sentences:
            return ""

        available = list(
            self.sentences
        )

        selected = []

        for sentence in available:
            projected = self._joined_length(
                selected + [sentence]
            )

            if (
                selected
                and projected
                > CONTEXT_MAX_CHARACTERS
            ):
                break

            selected.append(
                sentence
            )

            if (
                len(selected)
                >= CONTEXT_MAX_SENTENCES
                or projected
                >= CONTEXT_TARGET_CHARACTERS
            ):
                break

        selected_length = self._joined_length(
            selected
        )

        hard_limit_reached = (
            len(selected)
            >= CONTEXT_MAX_SENTENCES
            or selected_length
            >= CONTEXT_MAX_CHARACTERS
        )

        target_reached = (
            selected_length
            >= CONTEXT_TARGET_CHARACTERS
            and len(selected)
            >= CONTEXT_MIN_SENTENCES
        )

        if (
            not force
            and not hard_limit_reached
            and not target_reached
        ):
            return ""

        for _ in range(
            len(selected)
        ):
            self.sentences.popleft()

        return " ".join(
            selected
        ).strip()

    def _flush(
        self,
        force: bool,
        include_partial: bool
    ) -> list[str]:
        blocks = []

        while self.sentences:
            block = self._build_sentence_block(
                force=force
            )

            if not block:
                break

            blocks.append(
                block
            )

            if not force:
                break

        if (
            include_partial
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
            "CONTEXT_STATE",
            {
                "sentences": list(
                    self.sentences
                ),
                "partial": self.partial,
                "characters": (
                    self._total_characters()
                ),
            }
        )

        block_age = (
            now - self.block_started
            if self.block_started is not None
            else 0.0
        )

        hard_limit_reached = (
            len(self.sentences)
            >= CONTEXT_MAX_SENTENCES
            or self._sentence_characters()
            >= CONTEXT_MAX_CHARACTERS
        )

        target_reached = (
            len(self.sentences)
            >= CONTEXT_MIN_SENTENCES
            and self._sentence_characters()
            >= CONTEXT_TARGET_CHARACTERS
        )

        waited_too_long = (
            block_age
            >= CONTEXT_MAX_WAIT_SECONDS
        )

        if (
            not hard_limit_reached
            and not target_reached
            and not waited_too_long
        ):
            return []

        # Bei Zeitablauf vollständige Sätze bevorzugen. Nur wenn noch
        # überhaupt kein Satzende vorliegt, muss der Teiltext raus.
        include_partial = (
            waited_too_long
            and not self.sentences
        )

        blocks = self._flush(
            force=(
                hard_limit_reached
                or waited_too_long
            ),
            include_partial=include_partial,
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

        # Bei einer Pause vollständige Sätze sofort ausgeben. Der noch
        # laufende Satz bleibt erhalten. Nur wenn es gar kein Satzende
        # gibt, wird der Teiltext freigegeben.
        blocks = self._flush(
            force=True,
            include_partial=(
                not self.sentences
            ),
        )

        self._log(
            "CONTEXT_FLUSH",
            blocks
        )

        return blocks

    def flush_all(
        self
    ) -> list[str]:
        blocks = self._flush(
            force=True,
            include_partial=True,
        )

        self._log(
            "CONTEXT_FINAL_FLUSH",
            blocks
        )

        return blocks
