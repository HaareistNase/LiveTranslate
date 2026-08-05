import requests

from config import (
    OLLAMA_GENERATE_URL,
    OLLAMA_MODEL,
    OLLAMA_TAGS_URL,
)


class Translator:
    def check_ollama(self) -> None:
        response = requests.get(
            OLLAMA_TAGS_URL,
            timeout=10
        )
        response.raise_for_status()

    def translate_to_german(
        self,
        text: str,
        source_language: str
    ) -> str:
        prompt = f"""
You are a highly accurate professional subtitle translator.

The detected source language is: {source_language}

Translate the following spoken transcript into fluent,
natural and grammatically correct German subtitles.

Rules:
- Preserve the complete meaning.
- Correct obvious speech-recognition mistakes only when
  the intended meaning is clear from the context.
- Translate according to context, not word by word.
- Use idiomatic, natural German.
- Pay special attention to German grammar, articles,
  cases, prepositions and verb choice.
- Preserve names, numbers and technical terms.
- Do not invent information.
- Do not explain or comment.
- Do not summarize.
- Do not answer the speaker.
- Do not add introductions or quotation marks.
- If the source is already German, correct only obvious
  recognition and grammar errors.
- Output only the finished German subtitle text.

Transcript:
{text}
""".strip()

        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0.05,
                    "num_ctx": 4096
                }
            },
            timeout=120
        )

        response.raise_for_status()

        response_data = response.json()

        return response_data.get(
            "response",
            ""
        ).strip()
