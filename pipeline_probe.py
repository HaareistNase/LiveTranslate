import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class PipelineProbe:
    """
    Reines Diagnoseprotokoll.

    Diese Klasse verändert keine Texte, Warteschlangen oder Timings.
    """

    def __init__(
        self,
        output_dir: str = "logs/pipeline_probe"
    ):
        directory = Path(
            output_dir
        )

        directory.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        self.path = directory / (
            f"pipeline_probe_{timestamp}.jsonl"
        )

        self.summary_path = directory / (
            f"pipeline_summary_{timestamp}.json"
        )

        self.lock = threading.Lock()
        self.started_at = time.monotonic()
        self.sequence = 0

        self.counts = {
            "packets": 0,
            "raw_items": 0,
            "tracker_outputs": 0,
            "context_inputs": 0,
            "context_blocks": 0,
            "queue_items": 0,
            "nllb_inputs": 0,
            "nllb_outputs": 0,
            "gui_outputs": 0,
        }

        self.characters = {
            "raw_items": 0,
            "tracker_outputs": 0,
            "context_inputs": 0,
            "context_blocks": 0,
            "queue_items": 0,
            "nllb_inputs": 0,
            "nllb_outputs": 0,
            "gui_outputs": 0,
        }

    @staticmethod
    def _clean_text(
        value: Any
    ) -> str:
        if value is None:
            return ""

        return " ".join(
            str(value).split()
        ).strip()

    @staticmethod
    def _item_key(
        item: dict[str, Any]
    ) -> str:
        return (
            f"{item.get('speaker', '')}|"
            f"{item.get('start', '')}"
        )

    def _write(
        self,
        event: str,
        payload: dict[str, Any]
    ) -> None:
        with self.lock:
            self.sequence += 1

            record = {
                "seq": self.sequence,
                "seconds": round(
                    time.monotonic()
                    - self.started_at,
                    3
                ),
                "event": event,
                **payload,
            }

            with self.path.open(
                "a",
                encoding="utf-8"
            ) as handle:
                handle.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        default=str
                    )
                    + "\n"
                )

    def _count_text(
        self,
        stage: str,
        text: str
    ) -> None:
        if stage in self.counts:
            self.counts[stage] += 1

        if stage in self.characters:
            self.characters[stage] += len(
                text
            )

    def packet(
        self,
        data: dict[str, Any],
        items: list[dict[str, Any]]
    ) -> None:
        self.counts["packets"] += 1

        self._write(
            "websocket_packet",
            {
                "packet_type": data.get("type"),
                "item_count": len(items),
                "language": (
                    data.get("language")
                    or data.get(
                        "detected_language"
                    )
                ),
                "keys": [
                    self._item_key(item)
                    for item in items
                ],
            }
        )

    def raw_item(
        self,
        item: dict[str, Any]
    ) -> None:
        text = self._clean_text(
            item.get("text")
        )

        self._count_text(
            "raw_items",
            text
        )

        self._write(
            "raw_item",
            {
                "key": self._item_key(item),
                "start": item.get("start"),
                "end": item.get("end"),
                "language": (
                    item.get("language")
                    or item.get(
                        "detected_language"
                    )
                ),
                "characters": len(text),
                "words": len(
                    text.split()
                ),
                "text": text,
            }
        )

    def tracker_output(
        self,
        item: dict[str, Any],
        text: str
    ) -> None:
        text = self._clean_text(text)

        if not text:
            return

        self._count_text(
            "tracker_outputs",
            text
        )

        self._write(
            "tracker_output",
            {
                "key": self._item_key(item),
                "characters": len(text),
                "words": len(
                    text.split()
                ),
                "text": text,
            }
        )

    def context_input(
        self,
        text: str
    ) -> None:
        text = self._clean_text(text)

        self._count_text(
            "context_inputs",
            text
        )

        self._write(
            "context_input",
            {
                "characters": len(text),
                "words": len(
                    text.split()
                ),
                "text": text,
            }
        )

    def context_output(
        self,
        reason: str,
        blocks: list[str]
    ) -> None:
        cleaned = [
            self._clean_text(block)
            for block in blocks
            if self._clean_text(block)
        ]

        for block in cleaned:
            self._count_text(
                "context_blocks",
                block
            )

        if cleaned:
            self._write(
                "context_output",
                {
                    "reason": reason,
                    "block_count": len(
                        cleaned
                    ),
                    "blocks": cleaned,
                }
            )

    def queue_item(
        self,
        text: str,
        language: str
    ) -> None:
        text = self._clean_text(text)

        self._count_text(
            "queue_items",
            text
        )

        self._write(
            "translation_queue",
            {
                "language": language,
                "characters": len(text),
                "words": len(
                    text.split()
                ),
                "text": text,
            }
        )

    def nllb_input(
        self,
        batch: list[tuple[str, str]]
    ) -> None:
        rows = []

        for text, language in batch:
            text = self._clean_text(text)

            self._count_text(
                "nllb_inputs",
                text
            )

            rows.append(
                {
                    "language": language,
                    "characters": len(text),
                    "words": len(
                        text.split()
                    ),
                    "text": text,
                }
            )

        self._write(
            "nllb_input",
            {
                "batch_size": len(rows),
                "items": rows,
            }
        )

    def nllb_output(
        self,
        translations: list[str]
    ) -> None:
        rows = []

        for text in translations:
            text = self._clean_text(text)

            self._count_text(
                "nllb_outputs",
                text
            )

            rows.append(
                {
                    "characters": len(text),
                    "words": len(
                        text.split()
                    ),
                    "text": text,
                }
            )

        self._write(
            "nllb_output",
            {
                "batch_size": len(rows),
                "items": rows,
            }
        )

    def gui_output(
        self,
        text: str
    ) -> None:
        text = self._clean_text(text)

        self._count_text(
            "gui_outputs",
            text
        )

        self._write(
            "gui_output",
            {
                "characters": len(text),
                "words": len(
                    text.split()
                ),
                "text": text,
            }
        )

    def finish(self) -> None:
        summary = {
            "duration_seconds": round(
                time.monotonic()
                - self.started_at,
                3
            ),
            "counts": self.counts,
            "characters": self.characters,
            "probe_file": str(
                self.path
            ),
        }

        self.summary_path.write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        self._write(
            "session_finish",
            summary
        )
