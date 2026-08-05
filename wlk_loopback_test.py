import asyncio
import json
import warnings

import numpy as np


WS_URL = "ws://localhost:8000/asr?language=ru&mode=diff"

SPEAKER_NAME = "Lautsprecher (Sound BlasterX G6)"

SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.5
CHUNK_FRAMES = int(
    SAMPLE_RATE * CHUNK_SECONDS
)


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


def float32_to_pcm16(
    audio: np.ndarray
) -> bytes:
    pcm = (
        audio * 32767.0
    ).astype(
        "<i2"
    )

    return pcm.tobytes()


async def receive_results(
    websocket
) -> None:
    committed_lines = []

    async for message in websocket:
        data = json.loads(
            message
        )

        message_type = data.get(
            "type"
        )

        if message_type == "config":
            print(
                "Server verbunden."
            )
            print(
                "PCM-Modus:",
                data.get(
                    "useAudioWorklet"
                )
            )
            print()
            continue

        if message_type == "ready_to_stop":
            print()
            print(
                "Server hat die Verarbeitung beendet."
            )
            break

        if message_type == "snapshot":
            committed_lines = list(
                data.get(
                    "lines",
                    []
                )
            )

        elif message_type == "diff":
            lines_pruned = data.get(
                "lines_pruned",
                0
            )

            if lines_pruned:
                del committed_lines[
                    :lines_pruned
                ]

            committed_lines.extend(
                data.get(
                    "new_lines",
                    []
                )
            )

        else:
            continue

        new_lines = data.get(
            "new_lines",
            []
        )

        for line in new_lines:
            text = line.get(
                "text"
            )

            if text:
                print(
                    "BESTÄTIGT:",
                    text
                )

        buffer_text = data.get(
            "buffer_transcription",
            ""
        ).strip()

        if buffer_text:
            print(
                "VORLÄUFIG:",
                buffer_text
            )


async def send_loopback_audio(
    websocket
) -> None:
    # SoundCard bewusst erst hier importieren.
    # Dadurch bleibt die COM-Initialisierung in diesem Thread.
    import soundcard as sc

    speaker = sc.get_speaker(
        SPEAKER_NAME
    )

    microphone = sc.get_microphone(
        speaker.name,
        include_loopback=True
    )

    print(
        "Loopback-Gerät:",
        speaker.name
    )
    print(
        "Firefox-Ton abspielen."
    )
    print(
        "Beenden mit Strg+C."
    )
    print()

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

            while True:
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


async def main() -> None:
    import websockets

    print(
        "Verbinde mit WhisperLiveKit ..."
    )

    async with websockets.connect(
        WS_URL,
        max_size=None,
        ping_interval=20,
        ping_timeout=20
    ) as websocket:

        receiver_task = asyncio.create_task(
            receive_results(
                websocket
            )
        )

        sender_task = asyncio.create_task(
            send_loopback_audio(
                websocket
            )
        )

        try:
            await sender_task

        except asyncio.CancelledError:
            pass

        finally:
            try:
                await websocket.send(
                    b""
                )
            except Exception:
                pass

            sender_task.cancel()

            try:
                await asyncio.wait_for(
                    receiver_task,
                    timeout=10
                )
            except asyncio.TimeoutError:
                receiver_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:
        print()
        print(
            "Loopback-Test beendet."
        )

    except Exception as error:
        print()
        print(
            "Fehler:"
        )
        print(
            error
        )