from faster_whisper import WhisperModel

from config import WHISPER_MODEL


class WhisperEngine:
    def __init__(self):
        self.model = WhisperModel(
            WHISPER_MODEL,
            device="cuda",
            compute_type="float16"
        )

    def transcribe(
        self,
        audio
    ) -> tuple[str, str]:
        segments, info = self.model.transcribe(
            audio,
            language=None,
            beam_size=8,
            vad_filter=True,
            condition_on_previous_text=False,
            temperature=0.0
        )

        text_parts: list[str] = []

        for segment in segments:
            text = segment.text.strip()

            if text:
                text_parts.append(
                    text
                )

        full_text = " ".join(
            text_parts
        ).strip()

        language = (
            info.language
            or "unknown"
        )

        return full_text, language
