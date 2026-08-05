import queue
import threading
import warnings
from collections import deque

import numpy as np

from config import (
    AUDIO_QUEUE_SIZE,
    CHUNK_SECONDS,
    MAX_NORMALIZATION_GAIN,
    MAX_SPEECH_SECONDS,
    MIN_ACTIVE_CHUNKS,
    MIN_SILENCE_THRESHOLD,
    MIN_SPEECH_SECONDS,
    NOISE_FLOOR_SMOOTHING,
    NOISE_MULTIPLIER,
    NORMALIZE_AUDIO,
    NORMALIZE_TARGET_PEAK,
    PRE_ROLL_SECONDS,
    SAMPLE_RATE,
    SILENCE_TO_COMMIT_SECONDS,
    SPEAKER_NAME,
)


class AudioEngine:
    def __init__(self, bridge):
        self.bridge = bridge

        self.audio_queue = queue.Queue(
            maxsize=AUDIO_QUEUE_SIZE
        )

        self.stop_event = threading.Event()
        self.thread = None

    @staticmethod
    def to_mono_float32(
        audio: np.ndarray
    ) -> np.ndarray:
        if audio.ndim > 1:
            audio = np.mean(
                audio,
                axis=1
            )

        return audio.astype(
            np.float32
        )

    @staticmethod
    def calculate_rms(
        audio: np.ndarray
    ) -> float:
        if audio.size == 0:
            return 0.0

        squared = np.square(
            audio,
            dtype=np.float32
        )

        return float(
            np.sqrt(
                np.mean(squared)
            )
        )

    @staticmethod
    def normalize_audio(
        audio: np.ndarray
    ) -> np.ndarray:
        """
        Hebt leise Abschnitte an, ohne laute Abschnitte
        zu übersteuern.
        """

        if not NORMALIZE_AUDIO:
            return audio

        if audio.size == 0:
            return audio

        peak = float(
            np.max(
                np.abs(audio)
            )
        )

        if peak < 0.00001:
            return audio

        required_gain = (
            NORMALIZE_TARGET_PEAK
            / peak
        )

        gain = min(
            required_gain,
            MAX_NORMALIZATION_GAIN
        )

        # Bereits ausreichend lautes Audio nicht absenken.
        gain = max(
            1.0,
            gain
        )

        normalized = audio * gain

        return np.clip(
            normalized,
            -1.0,
            1.0
        ).astype(
            np.float32
        )

    def enqueue_audio(
        self,
        speech_chunks: list[np.ndarray],
        speech_seconds: float
    ) -> None:
        if speech_seconds < MIN_SPEECH_SECONDS:
            return

        if not speech_chunks:
            return

        audio = np.concatenate(
            speech_chunks
        ).astype(
            np.float32
        )

        audio = self.normalize_audio(
            audio
        )

        try:
            self.audio_queue.put(
                audio,
                timeout=1.0
            )

        except queue.Full:
            self.bridge.error_ready.emit(
                "Verarbeitung zu langsam – "
                "ein Abschnitt wurde verworfen"
            )

    def recording_worker(self) -> None:
        # SoundCard ausschließlich hier importieren.
        # Dadurch bleibt Qt/OLE im Hauptthread unberührt.
        import soundcard as sc

        try:
            speaker = sc.get_speaker(
                SPEAKER_NAME
            )

            microphone = sc.get_microphone(
                speaker.name,
                include_loopback=True
            )

        except Exception as error:
            self.bridge.error_ready.emit(
                f"Audiogerät: {error}"
            )
            return

        chunk_frames = int(
            SAMPLE_RATE
            * CHUNK_SECONDS
        )

        pre_roll_chunk_count = max(
            1,
            int(
                PRE_ROLL_SECONDS
                / CHUNK_SECONDS
            )
        )

        pre_roll_buffer = deque(
            maxlen=pre_roll_chunk_count
        )

        speech_chunks: list[np.ndarray] = []

        speech_seconds = 0.0
        silence_seconds = 0.0
        speech_active = False

        consecutive_active_chunks = 0

        # Startwert für die adaptive Rauschschwelle.
        noise_floor = MIN_SILENCE_THRESHOLD

        self.bridge.status_ready.emit(
            "Bereit · Warte auf Sprache"
        )

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=(
                        r".*data discontinuity "
                        r"in recording.*"
                    )
                )

                with microphone.recorder(
                    samplerate=SAMPLE_RATE
                ) as recorder:

                    while not self.stop_event.is_set():
                        chunk = recorder.record(
                            numframes=chunk_frames
                        )

                        chunk = self.to_mono_float32(
                            chunk
                        )

                        rms = self.calculate_rms(
                            chunk
                        )

                        # Den Grundpegel nur anpassen, solange
                        # kein Sprachabschnitt aktiv ist.
                        if not speech_active:
                            noise_floor = (
                                NOISE_FLOOR_SMOOTHING
                                * noise_floor
                                + (
                                    1.0
                                    - NOISE_FLOOR_SMOOTHING
                                )
                                * rms
                            )

                        dynamic_threshold = max(
                            MIN_SILENCE_THRESHOLD,
                            noise_floor
                            * NOISE_MULTIPLIER
                        )

                        contains_audio = (
                            rms
                            >= dynamic_threshold
                        )

                        if not speech_active:
                            pre_roll_buffer.append(
                                chunk
                            )

                        if contains_audio:
                            consecutive_active_chunks += 1
                        else:
                            consecutive_active_chunks = 0

                        speech_start_confirmed = (
                            not speech_active
                            and consecutive_active_chunks
                            >= MIN_ACTIVE_CHUNKS
                        )

                        if speech_start_confirmed:
                            speech_active = True

                            # Audio direkt vor dem erkannten Start
                            # mitnehmen, damit leise Satzanfänge
                            # nicht verloren gehen.
                            speech_chunks = list(
                                pre_roll_buffer
                            )

                            speech_seconds = (
                                len(speech_chunks)
                                * CHUNK_SECONDS
                            )

                            silence_seconds = 0.0

                            self.bridge.status_ready.emit(
                                "Sprache erkannt · "
                                "Aufnahme läuft"
                            )

                        elif speech_active:
                            speech_chunks.append(
                                chunk
                            )

                            speech_seconds += (
                                CHUNK_SECONDS
                            )

                            if contains_audio:
                                silence_seconds = 0.0
                            else:
                                silence_seconds += (
                                    CHUNK_SECONDS
                                )

                        commit_for_silence = (
                            speech_active
                            and silence_seconds
                            >= SILENCE_TO_COMMIT_SECONDS
                        )

                        commit_for_length = (
                            speech_active
                            and speech_seconds
                            >= MAX_SPEECH_SECONDS
                        )

                        if (
                            commit_for_silence
                            or commit_for_length
                        ):
                            self.enqueue_audio(
                                speech_chunks,
                                speech_seconds
                            )

                            speech_chunks = []
                            speech_seconds = 0.0
                            silence_seconds = 0.0
                            speech_active = False
                            consecutive_active_chunks = 0

                            pre_roll_buffer.clear()

                            self.bridge.status_ready.emit(
                                "Abschnitt abgeschlossen"
                            )

        except Exception as error:
            if not self.stop_event.is_set():
                self.bridge.error_ready.emit(
                    f"Audioaufnahme: {error}"
                )

    def start(self) -> None:
        self.thread = threading.Thread(
            target=self.recording_worker,
            name="RecordingWorker",
            daemon=True
        )

        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

        try:
            self.audio_queue.put_nowait(
                None
            )

        except queue.Full:
            pass

        if self.thread is not None:
            self.thread.join(
                timeout=3
            )