import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests

from config import (
    SERVER_START_TIMEOUT_SECONDS,
    SERVER_STOP_TIMEOUT_SECONDS,
    TORCH_DLL_PATH,
    WLK_BACKEND,
    WLK_HEALTH_URL,
    WLK_MODEL,
    WLK_POLICY,
)


class WhisperLiveKitServer:
    def __init__(
        self,
        status_callback=None,
        log_callback=None
    ):
        self.status_callback = status_callback
        self.log_callback = log_callback

        self.process = None
        self.log_thread = None

        self.stop_log_event = threading.Event()

        self.started_by_us = False
        self.current_language = None

    def status(
        self,
        text: str
    ) -> None:
        if self.status_callback is not None:
            self.status_callback(text)

    def log(
        self,
        text: str
    ) -> None:
        if self.log_callback is not None:
            self.log_callback(text)

    @staticmethod
    def is_healthy() -> bool:
        try:
            response = requests.get(
                WLK_HEALTH_URL,
                timeout=2
            )

            return response.ok

        except requests.RequestException:
            return False

    def build_environment(
        self
    ) -> dict[str, str]:
        environment = os.environ.copy()

        torch_dll_path = Path(
            TORCH_DLL_PATH
        )

        if torch_dll_path.exists():
            environment["PATH"] = (
                f"{torch_dll_path};"
                f"{environment.get('PATH', '')}"
            )

        return environment

    @staticmethod
    def find_wlk_executable() -> Path:
        scripts_directory = Path(
            sys.executable
        ).resolve().parent

        candidates = [
            scripts_directory / "wlk.exe",
            scripts_directory / "wlk",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            "Die WhisperLiveKit-Startdatei "
            "wlk.exe wurde neben python.exe "
            "nicht gefunden."
        )

    def build_command(
        self,
        language: str
    ) -> list[str]:
        wlk_executable = (
            self.find_wlk_executable()
        )

        return [
            str(wlk_executable),
            "--backend",
            WLK_BACKEND,
            "--backend-policy",
            WLK_POLICY,
            "--model",
            WLK_MODEL,
            "--language",
            language,
            "--pcm-input",
        ]

    def read_output(
        self
    ) -> None:
        if (
            self.process is None
            or self.process.stdout is None
        ):
            return

        for line in iter(
            self.process.stdout.readline,
            ""
        ):
            if self.stop_log_event.is_set():
                break

            line = line.rstrip()

            if line:
                self.log(line)

    def start(
        self,
        language: str
    ) -> None:
        if self.is_healthy():
            self.status(
                "WhisperLiveKit läuft bereits"
            )

            self.started_by_us = False
            self.current_language = language
            return

        self.status(
            "WhisperLiveKit wird gestartet"
        )

        creation_flags = 0

        if os.name == "nt":
            creation_flags = (
                subprocess.CREATE_NO_WINDOW
            )

        self.stop_log_event.clear()

        self.process = subprocess.Popen(
            self.build_command(language),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=self.build_environment(),
            creationflags=creation_flags
        )

        self.started_by_us = True
        self.current_language = language

        self.log_thread = threading.Thread(
            target=self.read_output,
            name="WhisperLiveKitLogReader",
            daemon=True
        )

        self.log_thread.start()

        deadline = (
            time.monotonic()
            + SERVER_START_TIMEOUT_SECONDS
        )

        while time.monotonic() < deadline:
            if self.is_healthy():
                self.status(
                    "WhisperLiveKit ist bereit"
                )
                return

            if (
                self.process is not None
                and self.process.poll() is not None
            ):
                raise RuntimeError(
                    "WhisperLiveKit wurde "
                    "unerwartet beendet."
                )

            time.sleep(0.5)

        raise TimeoutError(
            "WhisperLiveKit wurde nicht "
            "rechtzeitig bereit."
        )

    def stop(
        self
    ) -> None:
        self.stop_log_event.set()

        if (
            self.process is None
            or not self.started_by_us
        ):
            return

        if self.process.poll() is not None:
            self.process = None
            return

        self.status(
            "WhisperLiveKit wird beendet"
        )

        self.process.terminate()

        try:
            self.process.wait(
                timeout=SERVER_STOP_TIMEOUT_SECONDS
            )

        except subprocess.TimeoutExpired:
            self.process.kill()

        self.process = None
        self.started_by_us = False

        self.status(
            "WhisperLiveKit beendet"
        )
