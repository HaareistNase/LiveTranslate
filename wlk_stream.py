import asyncio
import json
import queue
import threading
import time
import warnings
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import requests
import websockets

from config import (
    AUDIO_ACTIVE_RMS_THRESHOLD,
    AUDIO_LEVEL_STATUS_INTERVAL,
    AUDIO_SILENCE_WARNING_SECONDS,
    CHUNK_SECONDS,
    LANGUAGE_NAMES,
    SAMPLE_RATE,
    TRANSLATION_BATCH_SIZE,
    TRANSLATION_BATCH_WAIT_SECONDS,
    WHISPER_TO_NLLB,
    WLK_HEALTH_URL,
    WLK_WS_URL,
)
from hallucination_filter import normalize_text
from nllb_translator import NLLBTranslator
from context_buffer import ContextBuffer
from transcript_assembler import TranscriptAssembler
from pipeline_logger import PipelineLogger


class WLKStream:
    def __init__(self, bridge, source_language='auto'):
        self.bridge = bridge
        self.stop_event = threading.Event()

        self.audio_queue = queue.Queue(
            maxsize=32
        )

        self.translation_queue = queue.Queue(
            maxsize=64
        )

        self.pipeline_logger = PipelineLogger(
            gui_callback=(
                self.bridge.server_log_ready.emit
            )
        )

        self.context_buffer = ContextBuffer(
            logger=self.pipeline_logger
        )

        self.transcript_assembler = TranscriptAssembler(
            logger=self.pipeline_logger
        )
        self.source_language = source_language
        self.current_language = (
            source_language
            if source_language != 'auto'
            else ''
        )

        self.translator = NLLBTranslator(
            status_callback=(
                self.bridge.status_ready.emit
            )
        )

        self.audio_thread = None
        self.translation_thread = None
        self.main_thread = None
        self.audio_level_callback = None
        self.audio_state_callback = None
        self.gpu_state_callback = None
        self.translator_state_callback = None

        # Vollständigkeitsdiagnose
        self.asr_update_count = 0
        self.asr_character_count = 0
        self.nllb_block_count = 0
        self.nllb_character_count = 0
        self.german_block_count = 0
        self.german_character_count = 0

    def emit_metrics(self) -> None:
        self.bridge.metrics_ready.emit(
            self.asr_update_count,
            self.asr_character_count,
            self.nllb_block_count,
            self.nllb_character_count,
            self.german_block_count,
            self.german_character_count
        )

    def check_server(self) -> None:
        response = requests.get(
            WLK_HEALTH_URL,
            timeout=10
        )

        response.raise_for_status()

    @staticmethod
    def to_mono_float32(
        audio: np.ndarray
    ) -> np.ndarray:
        if audio.ndim > 1:
            audio = np.mean(
                audio,
                axis=1
            )

        return np.clip(
            audio.astype(np.float32),
            -1.0,
            1.0
        )

    @staticmethod
    def calculate_rms(
        audio: np.ndarray
    ) -> float:
        if audio.size == 0:
            return 0.0

        return float(
            np.sqrt(
                np.mean(
                    np.square(
                        audio,
                        dtype=np.float32
                    )
                )
            )
        )

    @staticmethod
    def float32_to_pcm16(
        audio: np.ndarray
    ) -> bytes:
        return (
            audio * 32767.0
        ).astype("<i2").tobytes()

    def audio_worker(self) -> None:
        import soundcard as sc

        try:
            speaker = sc.default_speaker()

            if speaker is None:
                raise RuntimeError(
                    "Windows meldet kein "
                    "Standard-Ausgabegerät."
                )

            microphone = sc.get_microphone(
                speaker.name,
                include_loopback=True
            )


        except Exception as error:
            if self.audio_state_callback is not None:
                self.audio_state_callback(
                    False,
                    "Loopback-Fehler"
                )

            self.bridge.error_ready.emit(
                f"Loopback konnte nicht geöffnet "
                f"werden: {error}"
            )

            self.stop_event.set()
            return

        if self.audio_state_callback is not None:
            self.audio_state_callback(
                True,
                "Loopback geöffnet"
            )

        frames = int(
            SAMPLE_RATE * CHUNK_SECONDS
        )

        if self.reference_capture:
            reference_dir = Path(
                "logs/reference"
            )

            reference_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            self.reference_wav_path = str(
                reference_dir
                / f"reference_audio_{timestamp}.wav"
            )

            self.reference_wave_file = (
                wave.open(
                    self.reference_wav_path,
                    "wb"
                )
            )

            self.reference_wave_file.setnchannels(
                1
            )

            self.reference_wave_file.setsampwidth(
                2
            )

            self.reference_wave_file.setframerate(
                SAMPLE_RATE
            )

        last_status_time = 0.0
        last_active_time = time.monotonic()
        active_audio_seen = False

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r".*data discontinuity.*"
                )

                with microphone.recorder(
                    samplerate=SAMPLE_RATE
                ) as recorder:

                    while not self.stop_event.is_set():
                        audio = recorder.record(
                            numframes=frames
                        )

                        audio = self.to_mono_float32(
                            audio
                        )

                        rms = self.calculate_rms(
                            audio
                        )

                        now = time.monotonic()

                        if (
                            rms
                            >= AUDIO_ACTIVE_RMS_THRESHOLD
                        ):
                            active_audio_seen = True
                            last_active_time = now

                        if (
                            now - last_status_time
                            >= AUDIO_LEVEL_STATUS_INTERVAL
                        ):
                            if self.audio_level_callback is not None:
                                self.audio_level_callback(rms)

                            if (
                                not active_audio_seen
                                or now - last_active_time
                                >= AUDIO_SILENCE_WARNING_SECONDS
                            ):
                                self.bridge.status_ready.emit(
                                    "Kein Systemton erkannt"
                                )

                            last_status_time = now

                        pcm_bytes = (
                            self.float32_to_pcm16(
                                audio
                            )
                        )

                        if (
                            self.reference_wave_file
                            is not None
                        ):
                            self.reference_wave_file.writeframes(
                                pcm_bytes
                            )

                        try:
                            self.audio_queue.put(
                                pcm_bytes,
                                timeout=1.0
                            )

                        except queue.Full:
                            self.bridge.error_ready.emit(
                                "Audio-Warteschlange voll"
                            )

        except Exception as error:
            if not self.stop_event.is_set():
                self.bridge.error_ready.emit(
                    f"Audioaufnahme: {error}"
                )

                self.stop_event.set()

        finally:
            if self.reference_wave_file is not None:
                try:
                    self.reference_wave_file.close()
                except Exception:
                    pass

                self.reference_wave_file = None

    def collect_translation_batch(
        self,
        first_item
    ) -> list[tuple[str, str]]:
        batch = [
            first_item
        ]

        deadline = (
            time.monotonic()
            + TRANSLATION_BATCH_WAIT_SECONDS
        )

        while (
            len(batch)
            < TRANSLATION_BATCH_SIZE
        ):
            remaining = (
                deadline
                - time.monotonic()
            )

            if remaining <= 0:
                break

            try:
                item = self.translation_queue.get(
                    timeout=remaining
                )

            except queue.Empty:
                break

            if item is None:
                self.translation_queue.task_done()
                self.stop_event.set()
                break

            batch.append(item)

        return batch

    def translation_worker(self) -> None:
        try:
            if self.gpu_state_callback is not None:
                self.gpu_state_callback(
                    True,
                    "CUDA erkannt"
                )

            if self.translator_state_callback is not None:
                self.translator_state_callback(
                    False,
                    "NLLB wird geladen"
                )

            self.translator.load()

            if self.translator_state_callback is not None:
                self.translator_state_callback(
                    True,
                    "NLLB bereit"
                )

        except Exception as error:
            if self.gpu_state_callback is not None:
                self.gpu_state_callback(
                    False,
                    "CUDA nicht verfügbar"
                )

            if self.translator_state_callback is not None:
                self.translator_state_callback(
                    False,
                    "NLLB-Fehler"
                )

            self.bridge.error_ready.emit(
                f"NLLB: {error}"
            )

            self.stop_event.set()
            return

        while not self.stop_event.is_set():
            try:
                first_item = (
                    self.translation_queue.get(
                        timeout=0.5
                    )
                )

            except queue.Empty:
                continue

            if first_item is None:
                self.translation_queue.task_done()
                break

            batch = self.collect_translation_batch(
                first_item
            )

            try:
                self.bridge.status_ready.emit(
                    f"Übersetze "
                    f"{len(batch)} Abschnitt(e) ..."
                )

                self.pipeline_logger.log(
                    "NLLB_INPUT_BATCH",
                    [
                        {
                            "source_text": source_text,
                            "language": language,
                        }
                        for source_text, language
                        in batch
                    ]
                )

                translations = (
                    self.translator.translate_batch(
                        batch
                    )
                )

                self.pipeline_logger.log(
                    "NLLB_OUTPUT_BATCH",
                    translations
                )

                for (
                    source_text,
                    language
                ), german in zip(
                    batch,
                    translations
                ):
                    if not german:
                        continue

                    self.pipeline_logger.log(
                        "GUI_SUBTITLE",
                        german
                    )

                    self.german_block_count += 1
                    self.german_character_count += len(
                        german
                    )

                    self.bridge.subtitle_ready.emit(
                        german
                    )

                    self.emit_metrics()

                    name = LANGUAGE_NAMES.get(
                        language,
                        language
                    )

                    self.bridge.status_ready.emit(
                        f"Bereit · Sprache: {name}"
                    )

            except Exception as error:
                self.bridge.error_ready.emit(
                    f"Übersetzung: {error}"
                )

            finally:
                for _ in batch:
                    self.translation_queue.task_done()

    def enqueue_segments(
        self,
        segments: list[str]
    ) -> None:
        if (
            not self.current_language
            or self.current_language
            not in WHISPER_TO_NLLB
        ):
            return

        for segment in segments:
            segment = segment.strip()

            if not segment:
                continue

            self.pipeline_logger.log(
                "QUEUE_SEGMENT",
                {
                    "segment": segment,
                    "language": self.current_language,
                }
            )

            try:
                self.translation_queue.put(
                    (
                        segment,
                        self.current_language
                    ),
                    timeout=1.0
                )

                self.nllb_block_count += 1
                self.nllb_character_count += len(
                    segment
                )

                self.bridge.source_ready.emit(
                    segment
                )

                self.emit_metrics()

            except queue.Full:
                self.bridge.error_ready.emit(
                    "Übersetzungs-Warteschlange voll"
                )

    def update_language(
        self,
        data: dict,
        item: dict | None = None
    ) -> None:
        candidates = []

        if item:
            candidates.extend(
                [
                    item.get(
                        "detected_language"
                    ),
                    item.get(
                        "language"
                    ),
                    item.get(
                        "lang"
                    ),
                ]
            )

        candidates.extend(
            [
                data.get(
                    "detected_language"
                ),
                data.get(
                    "language"
                ),
                data.get(
                    "lang"
                ),
            ]
        )

        if self.source_language != "auto":
            self.current_language = self.source_language
            return

        for candidate in candidates:
            language = normalize_text(
                candidate
            ).lower()

            if language in WHISPER_TO_NLLB:
                self.current_language = language
                return

    async def send_audio(
        self,
        websocket
    ) -> None:
        while not self.stop_event.is_set():
            try:
                pcm = await asyncio.to_thread(
                    self.audio_queue.get,
                    True,
                    0.5
                )

            except queue.Empty:
                continue

            try:
                await websocket.send(
                    pcm
                )

            finally:
                self.audio_queue.task_done()

    async def receive(
        self,
        websocket
    ) -> None:
        while not self.stop_event.is_set():
            try:
                message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=0.5
                )

            except asyncio.TimeoutError:
                self.enqueue_segments(
                    self.context_buffer.flush_if_old()
                )
                continue

            data = json.loads(
                message
            )

            self.pipeline_logger.log(
                "RAW_WEBSOCKET",
                data
            )

            if data.get("type") == "config":
                self.update_language(
                    data
                )

                self.bridge.status_ready.emit(
                    "Verbunden · Sprache wird erkannt"
                )
                continue

            if data.get("type") == "ready_to_stop":
                break

            self.update_language(
                data
            )

            if data.get("type") == "diff":
                items = data.get(
                    "new_lines",
                    []
                )
            else:
                items = data.get(
                    "lines",
                    []
                )

            self.pipeline_logger.log(
                "RAW_ITEMS",
                items
            )

            for item in items:
                self.update_language(
                    data,
                    item
                )

                new_text = (
                    self.transcript_assembler
                    .add_item(item)
                )

                if not new_text:
                    self.pipeline_logger.log(
                        "ASSEMBLER_SKIPPED",
                        item.get("text")
                    )
                    continue

                self.asr_update_count += 1
                self.asr_character_count += len(
                    new_text
                )

                self.live_original_parts.append(
                    new_text
                )

                self.emit_metrics()

                self.enqueue_segments(
                    self.context_buffer.add_confirmed(
                        new_text
                    )
                )

            self.enqueue_segments(
                self.context_buffer.flush_if_old()
            )

    async def run_async(self) -> None:
        websocket_url = (
            'ws://localhost:8000/asr'
            f'?language={self.source_language}'
            '&mode=diff'
        )

        async with websockets.connect(
            websocket_url,
            max_size=None,
            ping_interval=20,
            ping_timeout=20
        ) as websocket:
            sender = asyncio.create_task(
                self.send_audio(
                    websocket
                )
            )

            receiver = asyncio.create_task(
                self.receive(
                    websocket
                )
            )

            try:
                await asyncio.gather(
                    sender,
                    receiver
                )

            finally:
                sender.cancel()
                receiver.cancel()

    def stream_worker(self) -> None:
        try:
            asyncio.run(
                self.run_async()
            )

        except Exception as error:
            if not self.stop_event.is_set():
                self.bridge.error_ready.emit(
                    f"WhisperLiveKit: {error}"
                )

    def get_live_original_text(
        self
    ) -> str:
        return " ".join(
            self.live_original_parts
        ).strip()

    def get_reference_wav_path(
        self
    ) -> str:
        return self.reference_wav_path

    def start(self) -> None:
        self.check_server()

        self.audio_thread = threading.Thread(
            target=self.audio_worker,
            name="AudioLoopbackWorker",
            daemon=True
        )

        self.translation_thread = threading.Thread(
            target=self.translation_worker,
            name="NLLBTranslationWorker",
            daemon=True
        )

        self.main_thread = threading.Thread(
            target=self.stream_worker,
            name="WhisperLiveKitWorker",
            daemon=True
        )

        self.audio_thread.start()
        self.translation_thread.start()
        self.main_thread.start()

    def stop(self) -> None:
        self.enqueue_segments(
            self.context_buffer.flush_all()
        )

        self.stop_event.set()

        try:
            self.translation_queue.put_nowait(
                None
            )

        except queue.Full:
            pass

        for thread in (
            self.audio_thread,
            self.translation_thread,
            self.main_thread,
        ):
            if thread is not None:
                thread.join(
                    timeout=3
                )
