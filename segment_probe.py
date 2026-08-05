import json
import threading
import time
from datetime import datetime
from pathlib import Path


class SegmentProbe:
    def __init__(self):
        folder = Path("logs/segment_probe")
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = folder / f"segment_probe_{stamp}.jsonl"
        self.lock = threading.Lock()
        self.started = time.monotonic()
        self.first_seen = {}
        self.previous_key = None

    def _write(self, payload):
        payload["session_seconds"] = round(
            time.monotonic() - self.started,
            3
        )
        with self.lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        default=str
                    )
                    + "\n"
                )

    @staticmethod
    def _key(item):
        start = item.get("start")
        if start is None:
            return None
        return (
            str(item.get("speaker", "")),
            str(start)
        )

    def record_packet(self, data, items):
        self._write({
            "event": "packet",
            "type": data.get("type"),
            "item_count": len(items),
            "language": (
                data.get("language")
                or data.get("detected_language")
            ),
        })

    def record_item(self, item):
        key = self._key(item)
        now = time.monotonic()

        if key is not None:
            first = self.first_seen.setdefault(key, now)
            age = now - first
        else:
            age = 0.0

        text = str(item.get("text", ""))

        self._write({
            "event": "item",
            "key": key,
            "new_key": (
                key is not None
                and key != self.previous_key
            ),
            "start": item.get("start"),
            "end": item.get("end"),
            "text_length": len(text),
            "word_count": len(text.split()),
            "line_age_seconds": round(age, 3),
            "text_tail": text[-160:],
        })

        if key is not None:
            self.previous_key = key

    def record_output(self, item, output):
        if not output:
            return

        self._write({
            "event": "tracker_output",
            "key": self._key(item),
            "output_length": len(output),
            "word_count": len(output.split()),
            "output": output,
        })

    def record_stop(self):
        self._write({"event": "stop"})
