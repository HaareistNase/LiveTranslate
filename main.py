import sys

import requests
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from subtitle_window import SubtitleWindow
from wlk_stream import WLKStream


class GuiBridge(QObject):
    subtitle_ready = Signal(str)
    status_ready = Signal(str)
    error_ready = Signal(str)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(
        "LiveTranslate Auto NLLB"
    )

    bridge = GuiBridge()
    stream = WLKStream(bridge)

    try:
        stream.start()
    except requests.RequestException as error:
        print(
            "WhisperLiveKit ist nicht erreichbar:"
        )
        print(error)
        return 1

    window = SubtitleWindow(
        bridge,
        stream.stop
    )
    window.show()

    result = app.exec()
    stream.stop()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
