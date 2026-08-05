import asyncio
import json
import re
import warnings

import numpy as np
import requests
import websockets


# ------------------------------------------------------------
# Einstellungen
# ------------------------------------------------------------

WS_URL = wslocalhost8000asrlanguage=ru&mode=diff

OLLAMA_URL = httplocalhost11434apigenerate
OLLAMA_MODEL = "qwen2.5:14b"

SPEAKER_NAME = Lautsprecher (Sound BlasterX G6)

SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.5
CHUNK_FRAMES = int(
    SAMPLE_RATE  CHUNK_SECONDS
)

# Falls WhisperLiveKit längere bestätigte Texte ohne Satzzeichen
# liefert, spätestens ab dieser Länge übersetzen.
MAX_PENDING_CHARACTERS = 180


# ------------------------------------------------------------
# Audio
# ------------------------------------------------------------

def to_mono_float32(
    audio np.ndarray
) - np.ndarray
    if audio.ndim  1
        audio = np.mean(
            audio,
            axis=1
        )

    return np.clip(
        audio.astype(np.float32),
        -1.0,
        1.0
    )


def float32_to_pcm16(
    audio np.ndarray
) - bytes
    pcm = (
        audio  32767.0
    ).astype(
        i2
    )

    return pcm.tobytes()


# ------------------------------------------------------------
# Textvergleich
# ------------------------------------------------------------

def normalize_spaces(
    text str
) - str
    return  .join(
        text.split()
    ).strip()


def get_new_suffix(
    previous str,
    current str
) - str
    
    Ermittelt den neu hinzugekommenen Teil einer teilweise
    kumulativen WhisperLiveKit-Ausgabe.
    

    previous = normalize_spaces(
        previous
    )

    current = normalize_spaces(
        current
    )

    if not current
        return 

    if not previous
        return current

    if current == previous
        return 

    if current.startswith(previous)
        return current[
            len(previous)
        ].strip()

    # Falls WLK den Beginn leicht verändert hat
    # größtmögliche Wortüberlappung zwischen dem Ende des
    # alten und dem Anfang des neuen Textes suchen.
    previous_words = previous.split()
    current_words = current.split()

    maximum_overlap = min(
        len(previous_words),
        len(current_words)
    )

    for overlap in range(
        maximum_overlap,
        0,
        -1
    )
        if (
            previous_words[-overlap]
            == current_words[overlap]
        )
            return  .join(
                current_words[overlap]
            ).strip()

    # Bei einer komplett neuen bestätigten Zeile
    # den gesamten Text übernehmen.
    return current


def split_complete_sentences(
    text str
) - tuple[list[str], str]
    
    Trennt vollständige Sätze vom noch unfertigen Rest.
    

    text = normalize_spaces(
        text
    )

    if not text
        return [], 

    matches = list(
        re.finditer(
            r".+?[.!?]+(?:\s+|$)",
            text
        )
    )

    if not matches
        return [], text

    sentences = [
        match.group(0).strip()
        for match in matches
    ]

    remainder_start = (
        matches[-1].end()
    )

    remainder = text[
        remainder_start
    ].strip()

    return sentences, remainder


# ------------------------------------------------------------
# Ollama  Qwen
# ------------------------------------------------------------

def translate_to_german(
    russian_text str
) - str
    prompt = f
You are a professional subtitle translator.

Translate the following Russian speech transcript into
fluent, natural and complete German subtitles.

Rules
- Preserve the complete meaning and tone.
- Translate according to context, not word by word.
- Correct only obvious speech-recognition errors when the
  intended wording is clear.
- Do not censor profanity, sexual language, insults or
  other explicit wording.
- Do not omit or soften content.
- Do not explain, summarize or comment.
- Do not answer the speaker.
- Output only the German translation.

Russian transcript
{russian_text}
.strip()

    response = requests.post(
        OLLAMA_URL,
        json={
            model OLLAMA_MODEL,
            prompt prompt,
            stream False,
            keep_alive 30m,
            options {
                temperature 0.05,
                num_ctx 4096
            }
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json().get(
        response,
        
    ).strip()


# ------------------------------------------------------------
# Übersetzungs-Worker
# ------------------------------------------------------------

async def translation_worker(
    translation_queue asyncio.Queue
) - None
    while True
        text = await translation_queue.get()

        if text is None
            translation_queue.task_done()
            break

        try
            german = await asyncio.to_thread(
                translate_to_german,
                text
            )

            if german
                print()
                print(DEUTSCH)
                print(german)
                print(-  80)

        except Exception as error
            print()
            print(
                Übersetzungsfehler
            )
            print(error)

        finally
            translation_queue.task_done()


# ------------------------------------------------------------
# WhisperLiveKit empfangen
# ------------------------------------------------------------

async def receive_results(
    websocket,
    translation_queue asyncio.Queue
) - None
    last_confirmed_text = 
    pending_text = 

    async for message in websocket
        data = json.loads(
            message
        )

        message_type = data.get(
            type
        )

        if message_type == config
            print(
                Mit WhisperLiveKit verbunden.
            )
            continue

        if message_type == ready_to_stop
            break

        if message_type not in (
            snapshot,
            diff
        )
            continue

        if message_type == snapshot
            confirmed_items = data.get(
                lines,
                []
            )
        else
            confirmed_items = data.get(
                new_lines,
                []
            )

        for item in confirmed_items
            confirmed_text = normalize_spaces(
                item.get(
                    text,
                    
                )
            )

            if not confirmed_text
                continue

            new_text = get_new_suffix(
                last_confirmed_text,
                confirmed_text
            )

            last_confirmed_text = (
                confirmed_text
            )

            if not new_text
                continue

            pending_text = normalize_spaces(
                f{pending_text} {new_text}
            )

            complete_sentences, pending_text = (
                split_complete_sentences(
                    pending_text
                )
            )

            for sentence in complete_sentences
                await translation_queue.put(
                    sentence
                )

            if (
                len(pending_text)
                = MAX_PENDING_CHARACTERS
            )
                await translation_queue.put(
                    pending_text
                )

                pending_text = 

    # Rest beim Beenden ebenfalls übersetzen
    if pending_text.strip()
        await translation_queue.put(
            pending_text.strip()
        )


# ------------------------------------------------------------
# Loopback senden
# ------------------------------------------------------------

async def send_loopback_audio(
    websocket
) - None
    import soundcard as sc

    speaker = sc.get_speaker(
        SPEAKER_NAME
    )

    microphone = sc.get_microphone(
        speaker.name,
        include_loopback=True
    )

    print(
        Loopback-Gerät,
        speaker.name
    )
    print(
        Russisches Video abspielen.
    )
    print(
        Beenden mit Strg+C.
    )
    print()

    with warnings.catch_warnings()
        warnings.filterwarnings(
            ignore,
            message=(
                r.data discontinuity 
                rin recording.
            )
        )

        with microphone.recorder(
            samplerate=SAMPLE_RATE
        ) as recorder

            while True
                audio = await asyncio.to_thread(
                    recorder.record,
                    CHUNK_FRAMES
                )

                audio = to_mono_float32(
                    audio
                )

                pcm_bytes = float32_to_pcm16(
                    audio
                )

                await websocket.send(
                    pcm_bytes
                )


# ------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------

async def main() - None
    translation_queue = asyncio.Queue()

    translator_task = asyncio.create_task(
        translation_worker(
            translation_queue
        )
    )

    print(
        Verbinde mit WhisperLiveKit …
    )

    async with websockets.connect(
        WS_URL,
        max_size=None,
        ping_interval=20,
        ping_timeout=20
    ) as websocket

        receiver_task = asyncio.create_task(
            receive_results(
                websocket,
                translation_queue
            )
        )

        sender_task = asyncio.create_task(
            send_loopback_audio(
                websocket
            )
        )

        try
            await sender_task

        finally
            sender_task.cancel()

            try
                await websocket.send(
                    b
                )
            except Exception
                pass

            try
                await asyncio.wait_for(
                    receiver_task,
                    timeout=10
                )
            except asyncio.TimeoutError
                receiver_task.cancel()

    await translation_queue.join()

    await translation_queue.put(
        None
    )

    await translator_task


if __name__ == __main__
    try
        asyncio.run(
            main()
        )

    except KeyboardInterrupt
        print()
        print(
            Liveübersetzung beendet.
        )

    except Exception as error
        print()
        print(
            Fehler
        )
        print(error)