import asyncio
import json
import queue
import threading
import time
import warnings
import wave
from datetime import datetime
from pathlib import Path
from collections import deque

import numpy as np
import requests
import websockets

from config import (
    AUDIO_ACTIVE_RMS_THRESHOLD,
    AUDIO_CLIP_LIMIT,
    AUDIO_GAIN_ENABLED,
    AUDIO_GAIN_MAX,
    AUDIO_GAIN_MIN_INPUT_RMS,
    AUDIO_GAIN_SMOOTHING,
    AUDIO_GAIN_TARGET_RMS,
    AUDIO_SIGNAL_PRESENT_RMS,
    AUDIO_LEVEL_STATUS_INTERVAL,
    AUDIO_SILENCE_WARNING_SECONDS,
    CHUNK_SECONDS,
    LANGUAGE_NAMES,
    SAMPLE_RATE,
    TRANSLATION_BATCH_SIZE,
    TRANSLATION_BATCH_WAIT_SECONDS,
    PENDING_LANGUAGE_SEGMENTS_MAX,
    WLK_ASR_WATCHDOG_SECONDS,
    WLK_CONNECT_RETRIES,
    WLK_CONNECT_RETRY_SECONDS,
    WHISPER_TO_NLLB,
    WLK_HEALTH_URL,
    WLK_DRAIN_TIMEOUT_SECONDS,
    WLK_WS_URL,
)
from hallucination_filter import normalize_text
from nllb_translator import NLLBTranslator
from context_buffer import ContextBuffer
from transcript_assembler import TranscriptAssembler
from pipeline_logger import PipelineLogger
from pipeline_probe import PipelineProbe
from raw_websocket_probe import RawWebSocketProbe


class WLKStream:
    def __init__(
        self,
        bridge,
        source_language='auto',
        reference_capture=False
    ):
        self.bridge = bridge
        self.source_language = source_language
        self.reference_capture = reference_capture

        self.reference_wav_path = ''
        self.reference_wave_file = None
        self.live_original_parts = []

        self.audio_stop_event = threading.Event()
        self.stop_event = threading.Event()
        self.server_ready_to_stop_event = threading.Event()
        self.stream_finished_event = threading.Event()

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

        self.pipeline_probe = PipelineProbe()
        self.raw_websocket_probe = RawWebSocketProbe()

        self.context_buffer = ContextBuffer(
            logger=self.pipeline_logger
        )

        self.transcript_assembler = TranscriptAssembler(
            logger=self.pipeline_logger
        )
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

        # Audio-Gain und Erkennungs-Watchdog
        self.smoothed_gain = 1.0
        self.last_audio_signal_time = 0.0
        self.last_asr_text_time = 0.0
        self.audio_signal_seen = False

        # Text darf während verspäteter/unklarer Spracherkennung
        # nicht verloren gehen.
        self.pending_language_segments = deque(
            maxlen=PENDING_LANGUAGE_SEGMENTS_MAX
        )

        self.last_unknown_language = ""

    def emit_metrics(self) -> None:
        self.bridge.metrics_ready.emit(
            self.asr_update_count,
            self.asr_character_count,
            self.nllb_block_count,
            self.nllb_character_count,
            self.german_block_count,
            self.german_character_count
        )

    def apply_adaptive_gain(
        self,
        audio: np.ndarray,
        rms: float
    ) -> np.ndarray:
        if (
            not AUDIO_GAIN_ENABLED
            or rms < AUDIO_GAIN_MIN_INPUT_RMS
        ):
            return audio

        desired_gain = min(
            AUDIO_GAIN_MAX,
            max(
                1.0,
                AUDIO_GAIN_TARGET_RMS / max(
                    rms,
                    1e-9
                )
            )
        )

        self.smoothed_gain = (
            (1.0 - AUDIO_GAIN_SMOOTHING)
            * self.smoothed_gain
            + AUDIO_GAIN_SMOOTHING
            * desired_gain
        )

        return np.clip(
            audio * self.smoothed_gain,
            -AUDIO_CLIP_LIMIT,
            AUDIO_CLIP_LIMIT
        ).astype(np.float32)

    @staticmethod
    def normalize_language_code(
        language
    ) -> str:
        value = normalize_text(
            language
        ).lower().replace(
            "_",
            "-"
        )

        aliases = {
            "rus": "ru",
            "russian": "ru",
            "eng": "en",
            "english": "en",
            "fra": "fr",
            "fre": "fr",
            "french": "fr",
            "spa": "es",
            "spanish": "es",
            "ukr": "uk",
            "ukrainian": "uk",
            "tha": "th",
            "thai": "th",
            "vie": "vi",
            "vietnamese": "vi",
            "zho": "zh",
            "chi": "zh",
            "zh-cn": "zh",
            "zh-tw": "zh",
            "chinese": "zh",
            "kor": "ko",
            "korean": "ko",
            "jpn": "ja",
            "japanese": "ja",
        }

        return aliases.get(
            value,
            value.split("-", 1)[0]
        )

    def flush_pending_language_segments(
        self
    ) -> None:
        if (
            not self.current_language
            or self.current_language
            not in WHISPER_TO_NLLB
        ):
            return

        while self.pending_language_segments:
            segment = (
                self.pending_language_segments
                .popleft()
            )

            self._enqueue_segment_with_language(
                segment,
                self.current_language
            )

    def _enqueue_segment_with_language(
        self,
        segment: str,
        language: str
    ) -> None:
        try:
            self.translation_queue.put(
                (
                    segment,
                    language
                ),
                timeout=1.0
            )

            self.pipeline_probe.queue_item(
                segment,
                language
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
            # Nicht blockieren: ältesten Eintrag verwerfen und den
            # aktuellen noch einmal versuchen.
            try:
                old_item = (
                    self.translation_queue
                    .get_nowait()
                )

                if old_item is not None:
                    self.translation_queue.task_done()

            except queue.Empty:
                pass

            try:
                self.translation_queue.put_nowait(
                    (
                        segment,
                        language
                    )
                )

            except queue.Full:
                self.bridge.error_ready.emit(
                    "Übersetzungs-Warteschlange "
                    "bleibt voll; Abschnitt verworfen."
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

                    while not self.audio_stop_event.is_set():
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
                            >= AUDIO_SIGNAL_PRESENT_RMS
                        ):
                            active_audio_seen = True
                            self.audio_signal_seen = True
                            last_active_time = now
                            self.last_audio_signal_time = now

                        audio = self.apply_adaptive_gain(
                            audio,
                            rms
                        )

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
                                    "Kein verwertbarer Systemton"
                                )

                            elif (
                                self.last_asr_text_time > 0
                                and now - self.last_asr_text_time
                                >= WLK_ASR_WATCHDOG_SECONDS
                            ):
                                self.bridge.status_ready.emit(
                                    "Systemton vorhanden · "
                                    "warte auf Spracherkennung …"
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

                self.pipeline_probe.nllb_input(
                    batch
                )

                translations = (
                    self.translator.translate_batch(
                        batch
                    )
                )

                self.pipeline_probe.nllb_output(
                    translations
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

                    self.pipeline_probe.gui_output(
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

            if (
                not self.current_language
                or self.current_language
                not in WHISPER_TO_NLLB
            ):
                self.pending_language_segments.append(
                    segment
                )

                self.bridge.status_ready.emit(
                    "Text erkannt · "
                    "Sprache wird noch zugeordnet …"
                )

                continue

            self._enqueue_segment_with_language(
                segment,
                self.current_language
            )

    def update_language(
        self,
        data: dict,
        item: dict | None = None
    ) -> None:
        if self.source_language != "auto":
            self.current_language = (
                self.source_language
            )

            self.flush_pending_language_segments()
            return

        candidates = []

        if item:
            candidates.extend(
                [
                    item.get("detected_language"),
                    item.get("language"),
                    item.get("lang"),
                ]
            )

        candidates.extend(
            [
                data.get("detected_language"),
                data.get("language"),
                data.get("lang"),
            ]
        )

        for candidate in candidates:
            if candidate is None:
                continue

            language = self.normalize_language_code(
                candidate
            )

            if not language:
                continue

            if language in WHISPER_TO_NLLB:
                changed = (
                    language
                    != self.current_language
                )

                self.current_language = language
                self.last_unknown_language = ""

                if changed:
                    name = LANGUAGE_NAMES.get(
                        language,
                        language
                    )

                    self.bridge.status_ready.emit(
                        f"Sprache erkannt: {name}"
                    )

                self.flush_pending_language_segments()
                return

            # Unbekannte oder nicht unterstützte Sprache niemals als
            # aktuellen Übersetzungscode setzen.
            if language != self.last_unknown_language:
                self.last_unknown_language = language

                self.bridge.status_ready.emit(
                    f"Sprache '{language}' erkannt, "
                    "aber nicht konfiguriert · "
                    "Erkennung läuft weiter"
                )

    async def send_audio(
        self,
        websocket
    ) -> None:
        while not self.stop_event.is_set():
            if (
                self.audio_stop_event.is_set()
                and self.audio_queue.empty()
            ):
                self.bridge.status_ready.emit(
                    "Audio beendet · "
                    "Whisper-Rückstand wird verarbeitet …"
                )

                # Offizielles WLK-Endsignal für PCM-Streaming.
                await websocket.send(b"")
                return

            try:
                pcm = await asyncio.to_thread(
                    self.audio_queue.get,
                    True,
                    0.25
                )

            except queue.Empty:
                continue

            try:
                await websocket.send(pcm)

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
                pending_text = (
                    self.transcript_assembler
                    .flush_stale()
                )

                if pending_text:
                    self.asr_update_count += 1
                    self.asr_character_count += len(
                        pending_text
                    )

                    self.live_original_parts.append(
                        pending_text
                    )

                    self.emit_metrics()

                    self.enqueue_segments(
                        self.context_buffer
                        .add_confirmed(
                            pending_text
                        )
                    )

                timeout_blocks = (
                    self.context_buffer.flush_if_old()
                )

                self.pipeline_probe.context_output(
                    "timeout_flush",
                    timeout_blocks
                )

                self.enqueue_segments(
                    timeout_blocks
                )

                continue

            data = json.loads(
                message
            )

            # Vollständiger unveränderter Mitschnitt direkt nach
            # json.loads(), noch vor jeder Interpretation.
            self.raw_websocket_probe.record(
                data
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
                self.server_ready_to_stop_event.set()

                self.bridge.status_ready.emit(
                    "Whisper-Rückstand vollständig verarbeitet"
                )

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

            self.pipeline_probe.packet(
                data,
                items
            )

            self.pipeline_logger.log(
                "RAW_ITEMS",
                items
            )

            for item in items:
                self.pipeline_probe.raw_item(
                    item
                )

                self.update_language(
                    data,
                    item
                )

                new_text = (
                    self.transcript_assembler
                    .add_item(item)
                )

                self.pipeline_probe.tracker_output(
                    item,
                    new_text
                )

                if not new_text:
                    self.pipeline_logger.log(
                        "LIVELINE_PENDING",
                        item.get("text")
                    )
                    continue

                self.last_asr_text_time = (
                    time.monotonic()
                )

                self.asr_update_count += 1
                self.asr_character_count += len(
                    new_text
                )

                self.live_original_parts.append(
                    new_text
                )

                self.emit_metrics()

                self.pipeline_probe.context_input(
                    new_text
                )

                context_blocks = (
                    self.context_buffer.add_confirmed(
                        new_text
                    )
                )

                self.pipeline_probe.context_output(
                    "confirmed_text",
                    context_blocks
                )

                self.enqueue_segments(
                    context_blocks
                )

            packet_flush_blocks = (
                self.context_buffer.flush_if_old()
            )

            self.pipeline_probe.context_output(
                "packet_flush",
                packet_flush_blocks
            )

            self.enqueue_segments(
                packet_flush_blocks
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
                self.send_audio(websocket)
            )

            receiver = asyncio.create_task(
                self.receive(websocket)
            )

            try:
                await sender

                await asyncio.wait_for(
                    receiver,
                    timeout=WLK_DRAIN_TIMEOUT_SECONDS
                )

            except asyncio.TimeoutError:
                self.bridge.error_ready.emit(
                    "WhisperLiveKit-Drain hat das "
                    "Zeitlimit überschritten."
                )

                receiver.cancel()

                try:
                    await receiver
                except asyncio.CancelledError:
                    pass

            finally:
                if not sender.done():
                    sender.cancel()

                if not receiver.done():
                    receiver.cancel()

    def stream_worker(self) -> None:
        last_error = None

        try:
            for attempt in range(
                1,
                WLK_CONNECT_RETRIES + 1
            ):
                if (
                    self.stop_event.is_set()
                    or self.audio_stop_event.is_set()
                ):
                    break

                try:
                    if attempt > 1:
                        self.bridge.status_ready.emit(
                            "Whisper-Verbindung wird "
                            f"neu aufgebaut ({attempt}/"
                            f"{WLK_CONNECT_RETRIES}) …"
                        )

                    asyncio.run(
                        self.run_async()
                    )

                    last_error = None
                    break

                except Exception as error:
                    last_error = error

                    if (
                        self.stop_event.is_set()
                        or self.audio_stop_event.is_set()
                    ):
                        break

                    time.sleep(
                        WLK_CONNECT_RETRY_SECONDS
                    )

            if (
                last_error is not None
                and not self.stop_event.is_set()
                and not self.audio_stop_event.is_set()
            ):
                self.bridge.error_ready.emit(
                    "WhisperLiveKit-Verbindung "
                    f"fehlgeschlagen: {last_error}"
                )

        finally:
            self.stream_finished_event.set()

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

        now = time.monotonic()
        self.last_audio_signal_time = now
        self.last_asr_text_time = now

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
        self.bridge.status_ready.emit(
            "Audioaufnahme wird beendet …"
        )

        self.audio_stop_event.set()

        if self.audio_thread is not None:
            self.audio_thread.join(timeout=5)

        if self.main_thread is not None:
            self.main_thread.join(
                timeout=WLK_DRAIN_TIMEOUT_SECONDS + 5
            )

        if (
            self.main_thread is not None
            and self.main_thread.is_alive()
        ):
            self.bridge.error_ready.emit(
                "WhisperLiveKit konnte nicht "
                "vollständig geleert werden."
            )

        pending_text = (
            self.transcript_assembler
            .flush_all()
        )

        if pending_text:
            self.asr_update_count += 1
            self.asr_character_count += len(
                pending_text
            )

            self.live_original_parts.append(
                pending_text
            )

            self.emit_metrics()

            self.pipeline_probe.context_input(
                pending_text
            )

            pending_blocks = (
                self.context_buffer.add_confirmed(
                    pending_text
                )
            )

            self.pipeline_probe.context_output(
                "stop_pending",
                pending_blocks
            )

            self.enqueue_segments(
                pending_blocks
            )

        final_blocks = (
            self.context_buffer.flush_all()
        )

        self.pipeline_probe.context_output(
            "stop_final_flush",
            final_blocks
        )

        self.enqueue_segments(
            final_blocks
        )

        self.bridge.status_ready.emit(
            "Restliche Übersetzungen werden verarbeitet …"
        )

        deadline = (
            time.monotonic()
            + WLK_DRAIN_TIMEOUT_SECONDS
        )

        while (
            self.translation_queue.unfinished_tasks
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)

        try:
            self.translation_queue.put_nowait(None)

        except queue.Full:
            self.bridge.error_ready.emit(
                "Übersetzungswarteschlange konnte "
                "nicht sauber beendet werden."
            )

        if self.translation_thread is not None:
            self.translation_thread.join(timeout=5)

        self.stop_event.set()

        self.pipeline_probe.finish()
        self.raw_websocket_probe.finish()

        self.bridge.status_ready.emit(
            "Verarbeitung abgeschlossen"
        )
