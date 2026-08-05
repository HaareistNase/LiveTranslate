import queue
import threading

from audio_engine import AudioEngine
from translator import Translator
from whisper_engine import WhisperEngine


class ProcessingEngine:
    def __init__(
        self,
        bridge,
        audio_engine: AudioEngine
    ):
        self.bridge = bridge
        self.audio_engine = audio_engine
        self.whisper = WhisperEngine()
        self.translator = Translator()
        self.stop_event = threading.Event()
        self.thread = None

    def worker(self) -> None:
        while not self.stop_event.is_set():
            try:
                audio = self.audio_engine.audio_queue.get(
                    timeout=0.5
                )
            except queue.Empty:
                continue

            if audio is None:
                self.audio_engine.audio_queue.task_done()
                break

            try:
                waiting = (
                    self.audio_engine.audio_queue.qsize()
                )

                if waiting > 0:
                    self.bridge.status_ready.emit(
                        f"Übersetze … "
                        f"{waiting} weiterer Abschnitt wartet"
                    )
                else:
                    self.bridge.status_ready.emit(
                        "Transkribiere und übersetze …"
                    )

                original_text, language = (
                    self.whisper.transcribe(
                        audio
                    )
                )

                if not original_text:
                    self.bridge.status_ready.emit(
                        "Keine verständliche Sprache erkannt"
                    )
                    continue

                german_text = (
                    self.translator.translate_to_german(
                        original_text,
                        language
                    )
                )

                if german_text:
                    self.bridge.subtitle_ready.emit(
                        german_text
                    )

                    self.bridge.status_ready.emit(
                        f"Bereit · Sprache: {language}"
                    )

            except Exception as error:
                self.bridge.error_ready.emit(
                    str(error)
                )

            finally:
                self.audio_engine.audio_queue.task_done()

    def start(self) -> None:
        self.thread = threading.Thread(
            target=self.worker,
            name="ProcessingWorker",
            daemon=True
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

        try:
            self.audio_engine.audio_queue.put_nowait(
                None
            )
        except queue.Full:
            pass

        if self.thread is not None:
            self.thread.join(
                timeout=3
            )
