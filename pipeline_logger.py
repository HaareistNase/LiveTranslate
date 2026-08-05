import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from config import (
    PIPELINE_DEBUG_ENABLED,
    PIPELINE_DEBUG_FILE,
    PIPELINE_DEBUG_GUI_TEXT_LIMIT,
)


class PipelineLogger:
    def __init__(
        self,
        gui_callback=None
    ):
        self.gui_callback = gui_callback
        self.lock = threading.Lock()
        self.path = Path(
            PIPELINE_DEBUG_FILE
        )

        if PIPELINE_DEBUG_ENABLED:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            self.path.write_text(
                "",
                encoding="utf-8"
            )

            self.log(
                "SESSION",
                "Pipeline-Diagnose gestartet"
            )

    @staticmethod
    def _format_value(
        value: Any
    ) -> str:
        if isinstance(
            value,
            (dict, list, tuple)
        ):
            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=str
            )

        return str(value)

    def log(
        self,
        stage: str,
        value: Any
    ) -> None:
        if not PIPELINE_DEBUG_ENABLED:
            return

        timestamp = datetime.now().strftime(
            "%H:%M:%S.%f"
        )[:-3]

        formatted = self._format_value(
            value
        )

        entry = (
            f"\n[{timestamp}] [{stage}]\n"
            f"{formatted}\n"
        )

        with self.lock:
            with self.path.open(
                "a",
                encoding="utf-8"
            ) as handle:
                handle.write(entry)

        if self.gui_callback is not None:
            compact = " ".join(
                formatted.split()
            )

            if (
                len(compact)
                > PIPELINE_DEBUG_GUI_TEXT_LIMIT
            ):
                compact = (
                    compact[
                        :PIPELINE_DEBUG_GUI_TEXT_LIMIT
                    ]
                    + " …"
                )

            self.gui_callback(
                f"[{stage}] {compact}"
            )
