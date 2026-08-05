import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class RawWebSocketProbe:
    """
    Vollständiger, unveränderter Mitschnitt aller empfangenen
    WhisperLiveKit-JSON-Pakete.

    Die Daten werden ausschließlich protokolliert und niemals verändert.
    """

    def __init__(
        self,
        output_dir: str = "logs/raw_websocket"
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

        self.raw_path = directory / (
            f"raw_websocket_{timestamp}.jsonl"
        )

        self.summary_path = directory / (
            f"raw_websocket_summary_{timestamp}.json"
        )

        self.lock = threading.Lock()
        self.started_at = time.monotonic()
        self.sequence = 0

        self.packet_count = 0
        self.total_json_characters = 0
        self.packet_types: dict[
            str,
            int
        ] = {}

        self.top_level_keys: dict[
            str,
            int
        ] = {}

        self.nonempty_line_packets = 0
        self.empty_line_packets = 0

    @staticmethod
    def _safe_json_size(
        data: Any
    ) -> int:
        try:
            return len(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    default=str
                )
            )

        except Exception:
            return 0

    @staticmethod
    def _extract_lines(
        data: dict[str, Any]
    ) -> list[Any]:
        if isinstance(
            data.get("new_lines"),
            list
        ):
            return data["new_lines"]

        if isinstance(
            data.get("lines"),
            list
        ):
            return data["lines"]

        return []

    @staticmethod
    def _line_has_text(
        line: Any
    ) -> bool:
        if not isinstance(
            line,
            dict
        ):
            return bool(
                str(line).strip()
            )

        return bool(
            str(
                line.get(
                    "text",
                    ""
                )
            ).strip()
        )

    def record(
        self,
        data: dict[str, Any]
    ) -> None:
        now = time.monotonic()

        packet_type = str(
            data.get(
                "type",
                "<missing>"
            )
        )

        lines = self._extract_lines(
            data
        )

        contains_nonempty_text = any(
            self._line_has_text(line)
            for line in lines
        )

        size = self._safe_json_size(
            data
        )

        with self.lock:
            self.sequence += 1
            self.packet_count += 1
            self.total_json_characters += size

            self.packet_types[packet_type] = (
                self.packet_types.get(
                    packet_type,
                    0
                )
                + 1
            )

            for key in data.keys():
                self.top_level_keys[key] = (
                    self.top_level_keys.get(
                        key,
                        0
                    )
                    + 1
                )

            if lines:
                if contains_nonempty_text:
                    self.nonempty_line_packets += 1
                else:
                    self.empty_line_packets += 1

            record = {
                "seq": self.sequence,
                "seconds": round(
                    now - self.started_at,
                    3
                ),
                "packet_type": packet_type,
                "json_characters": size,
                "top_level_keys": list(
                    data.keys()
                ),
                "line_count": len(lines),
                "contains_nonempty_text": (
                    contains_nonempty_text
                ),
                "payload": data,
            }

            with self.raw_path.open(
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

    def finish(
        self
    ) -> None:
        summary = {
            "duration_seconds": round(
                time.monotonic()
                - self.started_at,
                3
            ),
            "packet_count": self.packet_count,
            "total_json_characters": (
                self.total_json_characters
            ),
            "packet_types": self.packet_types,
            "top_level_keys": (
                self.top_level_keys
            ),
            "nonempty_line_packets": (
                self.nonempty_line_packets
            ),
            "empty_line_packets": (
                self.empty_line_packets
            ),
            "raw_file": str(
                self.raw_path
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
