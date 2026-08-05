import re
from collections import deque

import requests

from config import (
    OLLAMA_MODEL,
    OLLAMA_TAGS_URL,
    OLLAMA_URL,
    SOURCE_CONTEXT_SENTENCES,
)


class Translator:
    def __init__(self):
        self.source_context = deque(
            maxlen=SOURCE_CONTEXT_SENTENCES
        )

    def check_ollama(self) -> None:
        response = requests.get(
            OLLAMA_TAGS_URL,
            timeout=10
        )
        response.raise_for_status()

    @staticmethod
    def clean_model_output(text: str) -> str:
        text = text.strip()

        if "</think>" in text:
            text = text.rsplit(
                "</think>",
                1
            )[1].strip()

        text = re.sub(
            r"<think>.*?</think>",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()

        text = re.sub(
            r"^\s*(deutsch|übersetzung|untertitel|subtitle)\s*:\s*",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

        return text

    def translate_to_german(self, text: str) -> str:
        context = " ".join(
            self.source_context
        ).strip()

        prompt = f"""
You are a professional Russian-to-German subtitle translator.

The previous confirmed Russian speech is provided only as context.
Translate ONLY the CURRENT confirmed Russian text.

Important:
- Produce fluent, natural and grammatically correct German.
- Preserve meaning, tone, profanity and explicit language.
- Correct obvious ASR mistakes when the context makes the intended
  word clear. Prefer a contextually sensible correction over a
  literal translation of an impossible recognition.
- Do not invent information.
- Do not mention subtitles, transcription, DimaTorzok or the task.
- Do not explain your reasoning.
- Do not output labels such as "Übersetzung:" or "Untertitel:".
- Output only the final German translation of CURRENT TEXT.

PREVIOUS CONTEXT:
{context or "(none)"}

CURRENT TEXT:
{text}
""".strip()

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "think": False,
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 4096
                }
            },
            timeout=120
        )

        response.raise_for_status()

        result = self.clean_model_output(
            response.json().get(
                "response",
                ""
            )
        )

        self.source_context.append(
            text.strip()
        )

        return result
