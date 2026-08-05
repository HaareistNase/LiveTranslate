import sys
import threading
from collections import deque

from PySide6.QtCore import (
    QObject,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QCloseEvent,
    QFont,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from config import (
    DEBUG_MODE_DEFAULT,
    DEFAULT_SOURCE_LANGUAGE,
    SHOW_SERVER_LOG_DEFAULT,
    SOURCE_LANGUAGE_OPTIONS,
    SUBTITLE_HISTORY,
)
from server_manager import WhisperLiveKitServer
from wlk_stream import WLKStream
from reference_benchmark import run_reference_benchmark
from version import (
    BRANCH,
    VERSION,
    display_version,
)


class GuiBridge(QObject):
    subtitle_ready = Signal(str)
    source_ready = Signal(str)

    metrics_ready = Signal(
        int,
        int,
        int,
        int,
        int,
        int
    )

    reference_ready = Signal(dict)

    status_ready = Signal(str)
    error_ready = Signal(str)

    audio_level_ready = Signal(float)
    server_log_ready = Signal(str)

    server_state_ready = Signal(
        bool,
        str
    )

    audio_state_ready = Signal(
        bool,
        str
    )

    gpu_state_ready = Signal(
        bool,
        str
    )

    translator_state_ready = Signal(
        bool,
        str
    )

    controls_ready = Signal(
        bool
    )


class StatusIndicator(QWidget):
    def __init__(
        self,
        title: str
    ):
        super().__init__()

        self.dot = QLabel(
            "●"
        )

        self.dot.setFixedWidth(
            18
        )

        self.title = QLabel(
            title
        )

        self.detail = QLabel(
            "Nicht aktiv"
        )

        self.detail.setStyleSheet(
            "color: #888888;"
        )

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.setSpacing(
            5
        )

        layout.addWidget(
            self.dot
        )

        layout.addWidget(
            self.title
        )

        layout.addWidget(
            self.detail
        )

        self.set_state(
            False,
            "Nicht aktiv"
        )

    def set_state(
        self,
        active: bool,
        detail: str
    ) -> None:
        color = (
            "#49c16d"
            if active
            else "#777777"
        )

        self.dot.setStyleSheet(
            f"color: {color};"
            "font-size: 18px;"
        )

        self.detail.setText(
            detail
        )


class LiveTranslateWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.bridge = GuiBridge()

        self.debug_mode = (
            DEBUG_MODE_DEFAULT
        )

        self.server = WhisperLiveKitServer(
            status_callback=(
                self.bridge.status_ready.emit
            ),
            log_callback=(
                self.forward_server_log
            )
        )

        self.stream = None
        self.worker_thread = None
        self.running = False

        self.history = deque(
            maxlen=SUBTITLE_HISTORY
        )

        self.source_history = deque(
            maxlen=SUBTITLE_HISTORY
        )

        self.setWindowTitle(
            f"{display_version()} [{BRANCH}]"
        )

        self.resize(
            1080,
            670
        )

        self.setMinimumSize(
            780,
            520
        )

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #111111;
                color: white;
            }

            QLabel#TitleLabel {
                font-size: 23px;
                font-weight: 600;
            }

            QLabel#SubtitleLabel,
            QLabel#SourceLabel {
                background-color: #171717;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 18px;
            }

            QLabel#SourceLabel {
                color: #d0d0d0;
            }

            QLabel#MetricsLabel {
                color: #9fb9e8;
                background-color: #151b24;
                border: 1px solid #2d405f;
                border-radius: 6px;
                padding: 8px 12px;
            }

            QLabel#StatusLabel {
                color: #b5b5b5;
            }

            QFrame#StatusFrame {
                background-color: #171717;
                border: 1px solid #303030;
                border-radius: 7px;
                padding: 8px;
            }

            QPushButton {
                min-height: 38px;
                padding: 0 18px;
                border-radius: 6px;
                background-color: #2c2c2c;
                border: 1px solid #4a4a4a;
            }

            QPushButton:hover {
                background-color: #393939;
            }

            QPushButton:disabled {
                color: #777777;
                background-color: #222222;
            }

            QComboBox {
                min-height: 34px;
                padding: 0 10px;
                background-color: #242424;
                border: 1px solid #454545;
                border-radius: 5px;
            }

            QCheckBox {
                spacing: 7px;
            }

            QProgressBar {
                min-height: 18px;
                border: 1px solid #444444;
                border-radius: 5px;
                text-align: center;
                background-color: #202020;
            }

            QProgressBar::chunk {
                background-color: #4f8cff;
                border-radius: 4px;
            }

            QPlainTextEdit {
                background-color: #0c0c0c;
                border: 1px solid #333333;
                color: #bbbbbb;
                font-family: Consolas;
                font-size: 10pt;
            }
            """
        )

        central = QWidget()
        self.setCentralWidget(
            central
        )

        outer_layout = QVBoxLayout(
            central
        )

        outer_layout.setContentsMargins(
            20,
            18,
            20,
            18
        )

        outer_layout.setSpacing(
            13
        )

        top_row = QHBoxLayout()

        title_label = QLabel(
            display_version()
        )

        title_label.setObjectName(
            "TitleLabel"
        )

        top_row.addWidget(
            title_label
        )

        top_row.addStretch(
            1
        )

        self.debug_checkbox = QCheckBox(
            "Debugmodus"
        )

        self.debug_checkbox.setChecked(
            DEBUG_MODE_DEFAULT
        )

        self.debug_checkbox.toggled.connect(
            self.set_debug_mode
        )

        top_row.addWidget(
            self.debug_checkbox
        )

        outer_layout.addLayout(
            top_row
        )

        controls = QHBoxLayout()

        self.start_button = QPushButton(
            "Start"
        )

        self.stop_button = QPushButton(
            "Stopp"
        )

        self.stop_button.setEnabled(
            False
        )

        self.start_button.clicked.connect(
            self.start_translation
        )

        self.stop_button.clicked.connect(
            self.stop_translation
        )

        controls.addWidget(
            self.start_button
        )

        controls.addWidget(
            self.stop_button
        )

        controls.addSpacing(
            18
        )

        controls.addWidget(
            QLabel(
                "Quellsprache:"
            )
        )

        self.language_combo = QComboBox()

        for language_code, language_name in (
            SOURCE_LANGUAGE_OPTIONS.items()
        ):
            self.language_combo.addItem(
                language_name,
                language_code
            )

        default_index = (
            self.language_combo.findData(
                DEFAULT_SOURCE_LANGUAGE
            )
        )

        if default_index >= 0:
            self.language_combo.setCurrentIndex(
                default_index
            )

        controls.addWidget(
            self.language_combo
        )

        controls.addSpacing(
            18
        )

        self.reference_checkbox = QCheckBox(
            "Offline-Referenzvergleich"
        )

        self.reference_checkbox.setToolTip(
            "Zeichnet exakt denselben Systemton auf "
            "und transkribiert ihn nach Stopp noch einmal "
            "offline mit large-v3."
        )

        controls.addWidget(
            self.reference_checkbox
        )

        controls.addStretch(
            1
        )

        outer_layout.addLayout(
            controls
        )

        status_frame = QFrame()

        status_frame.setObjectName(
            "StatusFrame"
        )

        status_layout = QHBoxLayout(
            status_frame
        )

        status_layout.setContentsMargins(
            12,
            7,
            12,
            7
        )

        self.server_indicator = (
            StatusIndicator(
                "Whisper"
            )
        )

        self.audio_indicator = (
            StatusIndicator(
                "Audio"
            )
        )

        self.gpu_indicator = (
            StatusIndicator(
                "GPU"
            )
        )

        self.translator_indicator = (
            StatusIndicator(
                "Übersetzer"
            )
        )

        for indicator in (
            self.server_indicator,
            self.audio_indicator,
            self.gpu_indicator,
            self.translator_indicator,
        ):
            status_layout.addWidget(
                indicator
            )

        status_layout.addStretch(
            1
        )

        outer_layout.addWidget(
            status_frame
        )

        level_row = QHBoxLayout()

        level_row.addWidget(
            QLabel(
                "Systemton:"
            )
        )

        self.audio_level = QProgressBar()

        self.audio_level.setRange(
            0,
            1000
        )

        self.audio_level.setValue(
            0
        )

        self.audio_level.setFormat(
            "kein Pegel"
        )

        level_row.addWidget(
            self.audio_level,
            stretch=1
        )

        outer_layout.addLayout(
            level_row
        )

        original_heading = QLabel(
            "Original – tatsächlich an NLLB gesendet"
        )

        original_heading.setStyleSheet(
            "font-size: 14px;"
            "font-weight: 600;"
            "color: #b9c8df;"
        )

        outer_layout.addWidget(
            original_heading
        )

        self.source_label = QLabel(
            "Warte auf bestätigten Originaltext ..."
        )

        self.source_label.setObjectName(
            "SourceLabel"
        )

        self.source_label.setWordWrap(
            True
        )

        self.source_label.setAlignment(
            Qt.AlignLeft
            | Qt.AlignTop
        )

        source_font = QFont()
        source_font.setPointSize(
            14
        )

        self.source_label.setFont(
            source_font
        )

        outer_layout.addWidget(
            self.source_label,
            stretch=1
        )

        german_heading = QLabel(
            "Deutsch – NLLB-Ausgabe"
        )

        german_heading.setStyleSheet(
            "font-size: 14px;"
            "font-weight: 600;"
            "color: #b9c8df;"
        )

        outer_layout.addWidget(
            german_heading
        )

        self.subtitle_label = QLabel(
            "Start drücken, um die "
            "Live-Übersetzung zu beginnen."
        )

        self.subtitle_label.setObjectName(
            "SubtitleLabel"
        )

        self.subtitle_label.setWordWrap(
            True
        )

        self.subtitle_label.setAlignment(
            Qt.AlignLeft
            | Qt.AlignTop
        )

        subtitle_font = QFont()

        subtitle_font.setPointSize(
            18
        )

        self.subtitle_label.setFont(
            subtitle_font
        )

        outer_layout.addWidget(
            self.subtitle_label,
            stretch=2
        )

        self.metrics_label = QLabel(
            "Whisper: 0 Updates / 0 Zeichen  ·  "
            "An NLLB: 0 Blöcke / 0 Zeichen  ·  "
            "Deutsch: 0 Blöcke / 0 Zeichen"
        )

        self.metrics_label.setObjectName(
            "MetricsLabel"
        )

        self.metrics_label.setWordWrap(
            True
        )

        outer_layout.addWidget(
            self.metrics_label
        )

        self.status_label = QLabel(
            f"v{VERSION} · {BRANCH} · Bereit"
        )

        self.status_label.setObjectName(
            "StatusLabel"
        )

        outer_layout.addWidget(
            self.status_label
        )

        self.log_box = QPlainTextEdit()

        self.log_box.setReadOnly(
            True
        )

        self.log_box.setMaximumBlockCount(
            1000
        )

        self.log_box.setPlaceholderText(
            "WhisperLiveKit-Protokoll"
        )

        self.log_box.setVisible(
            SHOW_SERVER_LOG_DEFAULT
        )

        outer_layout.addWidget(
            self.log_box,
            stretch=1
        )

        self.bridge.subtitle_ready.connect(
            self.add_subtitle
        )

        self.bridge.source_ready.connect(
            self.add_source
        )

        self.bridge.metrics_ready.connect(
            self.update_metrics
        )

        self.bridge.reference_ready.connect(
            self.show_reference_result
        )

        self.bridge.status_ready.connect(
            self.set_status
        )

        self.bridge.error_ready.connect(
            self.show_error
        )

        self.bridge.audio_level_ready.connect(
            self.set_audio_level
        )

        self.bridge.server_log_ready.connect(
            self.append_log
        )

        self.bridge.server_state_ready.connect(
            self.server_indicator.set_state
        )

        self.bridge.audio_state_ready.connect(
            self.audio_indicator.set_state
        )

        self.bridge.gpu_state_ready.connect(
            self.gpu_indicator.set_state
        )

        self.bridge.translator_state_ready.connect(
            self.translator_indicator.set_state
        )

        self.bridge.controls_ready.connect(
            self.update_controls
        )

    def forward_server_log(
        self,
        text: str
    ) -> None:
        if self.debug_mode:
            self.bridge.server_log_ready.emit(
                text
            )

    def set_debug_mode(
        self,
        enabled: bool
    ) -> None:
        self.debug_mode = enabled
        self.log_box.setVisible(
            enabled
        )

        if enabled:
            self.append_log(
                "Debugmodus aktiviert"
            )

            self.append_log(
                "Vollständiges Protokoll: "
                "logs/pipeline_debug.log"
            )

    @staticmethod
    def escape_html(
        text: str
    ) -> str:
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def render_source_history(
        self
    ) -> None:
        if not self.source_history:
            self.source_label.setText(
                "Warte auf bestätigten Originaltext ..."
            )
            return

        parts = []

        for index, text in enumerate(
            self.source_history
        ):
            latest = (
                index
                == len(self.source_history) - 1
            )

            style = (
                "font-size: 17px;"
                "font-weight: 600;"
                "margin-top: 8px;"
                if latest
                else
                "font-size: 14px;"
                "color: #909090;"
                "margin-bottom: 5px;"
            )

            parts.append(
                f"<div style='{style}'>"
                f"{self.escape_html(text)}"
                "</div>"
            )

        self.source_label.setText(
            "".join(parts)
        )

    def add_source(
        self,
        text: str
    ) -> None:
        text = text.strip()

        if not text:
            return

        if (
            self.source_history
            and self.source_history[-1] == text
        ):
            return

        self.source_history.append(
            text
        )

        self.render_source_history()

    def update_metrics(
        self,
        asr_updates: int,
        asr_characters: int,
        nllb_blocks: int,
        nllb_characters: int,
        german_blocks: int,
        german_characters: int
    ) -> None:
        transfer_percent = (
            round(
                (
                    nllb_characters
                    / asr_characters
                )
                * 100
            )
            if asr_characters
            else 0
        )

        self.metrics_label.setText(
            f"Whisper bestätigt: "
            f"{asr_updates} Updates / "
            f"{asr_characters} Zeichen  ·  "
            f"An NLLB: "
            f"{nllb_blocks} Blöcke / "
            f"{nllb_characters} Zeichen "
            f"({transfer_percent}% des "
            f"bestätigten Textes)  ·  "
            f"Deutsch: "
            f"{german_blocks} Blöcke / "
            f"{german_characters} Zeichen"
        )

    def render_history(
        self
    ) -> None:
        if not self.history:
            self.subtitle_label.setText(
                "Warte auf übersetzten Text ..."
            )
            return

        parts = []

        history = list(
            self.history
        )

        for index, text in enumerate(
            history
        ):
            latest = (
                index
                == len(history) - 1
            )

            if latest:
                style = (
                    "font-size: 28px;"
                    "font-weight: 600;"
                    "margin-top: 14px;"
                )
            else:
                style = (
                    "font-size: 18px;"
                    "color: #aaaaaa;"
                    "margin-bottom: 8px;"
                )

            parts.append(
                f"<div style='{style}'>"
                f"{self.escape_html(text)}"
                "</div>"
            )

        self.subtitle_label.setText(
            "".join(parts)
        )

    def add_subtitle(
        self,
        text: str
    ) -> None:
        text = text.strip()

        if not text:
            return

        if (
            self.history
            and self.history[-1] == text
        ):
            return

        self.history.append(
            text
        )

        self.render_history()

    def show_reference_result(
        self,
        result: dict
    ) -> None:
        self.metrics_label.setText(
            "Offline-Referenz: "
            f"{result['offline_words']} Wörter / "
            f"{result['offline_characters']} Zeichen  ·  "
            "Live-Streaming: "
            f"{result['live_words']} Wörter / "
            f"{result['live_characters']} Zeichen  ·  "
            "Abdeckung: "
            f"{result['word_coverage_percent']}% Wörter / "
            f"{result['character_coverage_percent']}% Zeichen"
        )

        self.status_label.setText(
            "Referenzbericht gespeichert: "
            f"{result['report_path']}"
        )

    def set_status(
        self,
        text: str
    ) -> None:
        replacements = {
            "WhisperLiveKit ist bereit":
                "Whisper bereit",
            "Verbunden · Sprache wird erkannt":
                "Sprache wird erkannt",
            "Live-Übersetzung läuft":
                "Live-Übersetzung läuft",
            "WhisperLiveKit wird gestartet":
                "Whisper wird gestartet",
        }

        self.status_label.setText(
            replacements.get(
                text,
                text
            )
        )

    def show_error(
        self,
        text: str
    ) -> None:
        self.status_label.setText(
            f"Fehler: {text}"
        )

        self.append_log(
            f"FEHLER: {text}"
        )

    def set_audio_level(
        self,
        rms: float
    ) -> None:
        value = min(
            1000,
            max(
                0,
                int(rms * 15000)
            )
        )

        self.audio_level.setValue(
            value
        )

        self.audio_level.setFormat(
            f"RMS {rms:.6f}"
        )

        active = rms >= 0.0002

        self.audio_indicator.set_state(
            active,
            (
                "Signal aktiv"
                if active
                else "Kein Signal"
            )
        )

    def append_log(
        self,
        text: str
    ) -> None:
        self.log_box.appendPlainText(
            text
        )

    def update_controls(
        self,
        running: bool
    ) -> None:
        self.running = running

        self.start_button.setEnabled(
            not running
        )

        self.stop_button.setEnabled(
            running
        )

        self.language_combo.setEnabled(
            not running
        )

        self.reference_checkbox.setEnabled(
            not running
        )

    def start_translation(
        self
    ) -> None:
        if self.running:
            return

        self.history.clear()
        self.source_history.clear()

        self.render_history()
        self.render_source_history()

        self.update_metrics(
            0,
            0,
            0,
            0,
            0,
            0
        )

        self.update_controls(
            True
        )

        selected_language = (
            self.language_combo.currentData()
            or "auto"
        )

        reference_capture = (
            self.reference_checkbox.isChecked()
        )

        self.worker_thread = threading.Thread(
            target=self.start_worker,
            args=(
                selected_language,
                reference_capture
            ),
            name="LiveTranslateStarter",
            daemon=True
        )

        self.worker_thread.start()

    def start_worker(
        self,
        selected_language: str,
        reference_capture: bool
    ) -> None:
        try:
            self.bridge.server_state_ready.emit(
                False,
                "Wird gestartet"
            )

            self.server.start(
                selected_language
            )

            self.bridge.server_state_ready.emit(
                True,
                "Bereit"
            )

            self.stream = WLKStream(
                self.bridge,
                source_language=selected_language,
                reference_capture=reference_capture
            )

            self.stream.audio_level_callback = (
                self.bridge.audio_level_ready.emit
            )

            self.stream.audio_state_callback = (
                self.bridge.audio_state_ready.emit
            )

            self.stream.gpu_state_callback = (
                self.bridge.gpu_state_ready.emit
            )

            self.stream.translator_state_callback = (
                self.bridge.translator_state_ready.emit
            )

            self.stream.start()

            self.bridge.status_ready.emit(
                "Live-Übersetzung läuft"
            )

        except Exception as error:
            self.bridge.error_ready.emit(
                str(error)
            )

            self.bridge.server_state_ready.emit(
                False,
                "Fehler"
            )

            self.bridge.controls_ready.emit(
                False
            )

    def stop_translation(
        self
    ) -> None:
        if not self.running:
            return

        self.stop_button.setEnabled(
            False
        )

        thread = threading.Thread(
            target=self.stop_worker,
            name="LiveTranslateStopper",
            daemon=True
        )

        thread.start()

    def stop_worker(
        self
    ) -> None:
        reference_wav_path = ""
        live_original_text = ""
        reference_language = "auto"
        run_reference = False

        try:
            if self.stream is not None:
                run_reference = (
                    self.stream.reference_capture
                )

                reference_wav_path = (
                    self.stream
                    .get_reference_wav_path()
                )

                live_original_text = (
                    self.stream
                    .get_live_original_text()
                )

                reference_language = (
                    self.stream.source_language
                )

                self.stream.stop()
                self.stream = None

            self.server.stop()

            if (
                run_reference
                and reference_wav_path
            ):
                result = run_reference_benchmark(
                    reference_wav_path,
                    live_original_text,
                    reference_language,
                    progress_callback=(
                        self.bridge.status_ready.emit
                    )
                )

                self.bridge.reference_ready.emit(
                    result
                )

        except Exception as error:
            self.bridge.error_ready.emit(
                f"Referenzvergleich: {error}"
            )

        finally:
            self.bridge.server_state_ready.emit(
                False,
                "Gestoppt"
            )

            self.bridge.audio_state_ready.emit(
                False,
                "Gestoppt"
            )

            self.bridge.gpu_state_ready.emit(
                False,
                "Gestoppt"
            )

            self.bridge.translator_state_ready.emit(
                False,
                "Gestoppt"
            )

            self.bridge.status_ready.emit(
                "Gestoppt"
            )

            self.bridge.controls_ready.emit(
                False
            )

    def closeEvent(
        self,
        event: QCloseEvent
    ) -> None:
        try:
            if self.stream is not None:
                self.stream.stop()

            self.server.stop()

        except Exception:
            pass

        event.accept()


def main() -> int:
    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "LiveTranslate"
    )

    window = LiveTranslateWindow()

    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
