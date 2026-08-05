from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from config import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SUBTITLE_HISTORY,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)


class SubtitleWindow(QWidget):
    def __init__(self, bridge, on_close):
        super().__init__()

        self.on_close = on_close
        self.history = deque(
            maxlen=SUBTITLE_HISTORY
        )

        self.setWindowTitle(
            "LiveTranslate Auto NLLB"
        )

        self.setWindowFlags(
            Qt.Window
            | Qt.WindowStaysOnTopHint
        )

        self.resize(
            WINDOW_WIDTH,
            WINDOW_HEIGHT
        )

        self.setMinimumSize(
            MIN_WINDOW_WIDTH,
            MIN_WINDOW_HEIGHT
        )

        self.setStyleSheet(
            """
            QWidget {
                background-color: #111111;
            }
            QLabel#SubtitleLabel {
                color: white;
                background-color: #111111;
                padding: 22px;
            }
            QLabel#StatusLabel {
                color: #aaaaaa;
                background-color: #111111;
                padding: 6px 16px 12px 16px;
            }
            """
        )

        self.subtitle_label = QLabel(
            "Warte auf übersetzten Text ..."
        )
        self.subtitle_label.setObjectName(
            "SubtitleLabel"
        )
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setAlignment(
            Qt.AlignLeft
            | Qt.AlignVCenter
        )

        subtitle_font = QFont()
        subtitle_font.setPointSize(22)
        self.subtitle_label.setFont(
            subtitle_font
        )

        self.status_label = QLabel(
            "Modelle werden vorbereitet ..."
        )
        self.status_label.setObjectName(
            "StatusLabel"
        )

        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(
            status_font
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )
        layout.addWidget(
            self.subtitle_label,
            stretch=1
        )
        layout.addWidget(
            self.status_label
        )
        self.setLayout(layout)

        bridge.subtitle_ready.connect(
            self.add_subtitle
        )
        bridge.status_ready.connect(
            self.status_label.setText
        )
        bridge.error_ready.connect(
            self.show_error
        )

    @staticmethod
    def escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def add_subtitle(self, text: str) -> None:
        text = text.strip()

        if not text:
            return

        if self.history and self.history[-1] == text:
            return

        self.history.append(text)
        html = []

        for index, subtitle in enumerate(
            self.history
        ):
            latest = (
                index
                == len(self.history) - 1
            )

            if latest:
                style = (
                    "font-size: 28px;"
                    "font-weight: 600;"
                    "margin-top: 14px;"
                )
            else:
                style = (
                    "font-size: 19px;"
                    "color: #aaaaaa;"
                    "margin-bottom: 8px;"
                )

            html.append(
                f"<div style='{style}'>"
                f"{self.escape_html(subtitle)}"
                "</div>"
            )

        self.subtitle_label.setText(
            "".join(html)
        )

    def show_error(self, text: str) -> None:
        self.status_label.setText(
            f"Fehler: {text}"
        )

    def closeEvent(
        self,
        event: QCloseEvent
    ) -> None:
        self.on_close()
        event.accept()
