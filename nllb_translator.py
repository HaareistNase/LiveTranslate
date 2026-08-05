import os
import warnings

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
warnings.filterwarnings("ignore", message=".*max_new_tokens.*max_length.*")
warnings.filterwarnings("ignore", message=".*torch_dtype.*deprecated.*")

import threading

import torch
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
)

from config import (
    NLLB_BEAM_SIZE,
    NLLB_MAX_NEW_TOKENS,
    NLLB_MODEL,
    TARGET_LANGUAGE,
    WHISPER_TO_NLLB,
)


class NLLBTranslator:
    def __init__(
        self,
        status_callback=None
    ):
        self.status_callback = status_callback
        self.tokenizer = None
        self.model = None
        self.lock = threading.Lock()

    def status(
        self,
        text: str
    ) -> None:
        if self.status_callback is not None:
            self.status_callback(text)

    def load(self) -> None:
        if not torch.cuda.is_available():
            raise RuntimeError(
                "PyTorch erkennt keine CUDA-GPU."
            )

        self.status(
            "Lade NLLB-1.3B auf die GPU ..."
        )

        self.tokenizer = (
            AutoTokenizer.from_pretrained(
                NLLB_MODEL
            )
        )

        self.model = (
            AutoModelForSeq2SeqLM
            .from_pretrained(
                NLLB_MODEL,
                torch_dtype=torch.float16
            )
            .to("cuda")
            .eval()
        )

        self.status(
            "NLLB bereit · Warte auf Sprache"
        )

    def translate_batch(
        self,
        items: list[tuple[str, str]]
    ) -> list[str]:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError(
                "NLLB ist noch nicht geladen."
            )

        results = [
            ""
            for _ in items
        ]

        # NLLB braucht pro Batch eine gemeinsame Quellsprache.
        # Daher werden die vorbereiteten Segmente nach Sprache gruppiert.
        grouped: dict[str, list[tuple[int, str]]] = {}

        for index, (
            text,
            whisper_language
        ) in enumerate(items):
            source_language = WHISPER_TO_NLLB.get(
                whisper_language
            )

            if source_language is None:
                continue

            grouped.setdefault(
                source_language,
                []
            ).append(
                (
                    index,
                    text
                )
            )

        with self.lock:
            for source_language, group in grouped.items():
                indices = [
                    index
                    for index, _ in group
                ]

                texts = [
                    text
                    for _, text in group
                ]

                self.tokenizer.src_lang = (
                    source_language
                )

                inputs = self.tokenizer(
                    texts,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512
                ).to("cuda")

                forced_id = (
                    self.tokenizer
                    .convert_tokens_to_ids(
                        TARGET_LANGUAGE
                    )
                )

                with torch.inference_mode():
                    generated = self.model.generate(
                        **inputs,
                        forced_bos_token_id=forced_id,
                        num_beams=NLLB_BEAM_SIZE,
                        max_new_tokens=NLLB_MAX_NEW_TOKENS,
                        do_sample=False
                    )

                translations = (
                    self.tokenizer.batch_decode(
                        generated,
                        skip_special_tokens=True
                    )
                )

                for index, translation in zip(
                    indices,
                    translations
                ):
                    results[index] = " ".join(
                        translation.split()
                    ).strip()

        return results
