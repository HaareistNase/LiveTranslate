import sys

import requests
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from audio_engine import AudioEngine
from processing_engine import ProcessingEngine
from subtitle_window import SubtitleWindow
from translator import Translator


class GuiBridge(QObject):
    subtitle_ready = Signal(str)
    status_ready = Signal(str)
    error_ready = Signal(str)


def main() -> int:
    print("Prüfe Ollama …")

    translator = Translator()

    try:
        translator.check_ollama()
    except requests.RequestException as error:
        print()
        print(
            "Ollama ist nicht erreichbar."
        )
        print(
            "Bitte Ollama starten und "
            "das Programm erneut aufrufen."
        )
        print(error)
        return 1

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "LiveTranslate"
    )

    bridge = GuiBridge()

    audio_engine = AudioEngine(
        bridge
    )

    print("Lade Whisper …")

    processing_engine = ProcessingEngine(
        bridge,
        audio_engine
    )

    def shutdown() -> None:
        processing_engine.stop()
        audio_engine.stop()

    window = SubtitleWindow(
        bridge,
        shutdown
    )

    window.show()

    processing_engine.start()
    audio_engine.start()

    result = app.exec()

    shutdown()

    return result


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
