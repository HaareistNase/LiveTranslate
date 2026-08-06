import json
import re
from datetime import datetime
from pathlib import Path

from faster_whisper import WhisperModel

from config import (
    REFERENCE_BEAM_SIZE,
    REFERENCE_COMPUTE_TYPE,
    REFERENCE_MODEL,
    REFERENCE_OUTPUT_DIR,
)


_WORD_PATTERN = re.compile(
    r"\b[\w'-]+\b",
    re.UNICODE
)


def count_words(text: str) -> int:
    return len(
        _WORD_PATTERN.findall(text)
    )


def normalize_space(text: str) -> str:
    return " ".join(
        text.split()
    ).strip()


def run_reference_benchmark(
    wav_path: str,
    live_original_text: str,
    language: str,
    progress_callback=None
) -> dict:
    output_dir = Path(
        REFERENCE_OUTPUT_DIR
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    def progress(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    progress(
        "Offline-Referenzmodell wird geladen ..."
    )

    model = WhisperModel(
        REFERENCE_MODEL,
        device="cuda",
        compute_type=REFERENCE_COMPUTE_TYPE
    )

    fixed_language = (
        None
        if language == "auto"
        else language
    )

    progress(
        "Offline-Referenztranskription läuft ..."
    )

    segments, info = model.transcribe(
        wav_path,
        language=fixed_language,
        task="transcribe",
        beam_size=REFERENCE_BEAM_SIZE,
        vad_filter=False,
        condition_on_previous_text=True,
        word_timestamps=False
    )

    offline_parts = []

    for segment in segments:
        text = normalize_space(
            segment.text
        )

        if text:
            offline_parts.append(text)

    offline_text = normalize_space(
        " ".join(offline_parts)
    )

    live_text = normalize_space(
        live_original_text
    )

    live_words = count_words(
        live_text
    )

    offline_words = count_words(
        offline_text
    )

    word_coverage = (
        round(
            live_words
            / offline_words
            * 100
        )
        if offline_words
        else 0
    )

    character_coverage = (
        round(
            len(live_text)
            / len(offline_text)
            * 100
        )
        if offline_text
        else 0
    )

    result = {
        "detected_language": info.language,
        "language_probability": (
            info.language_probability
        ),
        "live_characters": len(live_text),
        "offline_characters": len(
            offline_text
        ),
        "live_words": live_words,
        "offline_words": offline_words,
        "word_coverage_percent": word_coverage,
        "character_coverage_percent": (
            character_coverage
        ),
        "live_text": live_text,
        "offline_text": offline_text,
        "wav_path": str(wav_path),
    }

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = output_dir / (
        f"reference_report_{timestamp}.json"
    )

    report_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    live_path = output_dir / (
        f"live_original_{timestamp}.txt"
    )

    live_path.write_text(
        live_text,
        encoding="utf-8"
    )

    offline_path = output_dir / (
        f"offline_reference_{timestamp}.txt"
    )

    offline_path.write_text(
        offline_text,
        encoding="utf-8"
    )

    result["report_path"] = str(
        report_path
    )

    progress(
        "Offline-Referenzvergleich abgeschlossen"
    )

    return result
