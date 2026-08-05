LiveTranslate v18.10-prefix – Präfix-basierter Tracker

Dieser Patch verändert ausschließlich:

- transcript_assembler.py
- version.py
- tests/test_prefix_tracker.py

Unverändert bleiben:

- main_gui.py
- wlk_stream.py
- context_buffer.py
- config.py
- Audio
- ASR-Zeitwerte
- Übersetzer

Neue Logik:

WhisperLiveKit kann dieselbe Startzeit sehr lange weiterführen.
Nach einer Zwischenfreigabe wird die Zeile deshalb nicht mehr gelöscht.

Der Tracker speichert dauerhaft:

- den neuesten vollständigen Whisper-Text
- den bereits an NLLB ausgegebenen Präfix

Bei späterem Wachstum derselben Zeile wird nur der neue Wort-Suffix
ausgegeben.

Beispiel:

1. Ausgabe:
   "Сейчас мои дети спят"

2. Neuer vollständiger WLK-Stand:
   "Сейчас мои дети спят я пока записываю это видео"

3. Neue Ausgabe:
   "я пока записываю это видео"

Der bereits ausgegebene Anfang erscheint niemals erneut.

Diesen Patch über den funktionierenden Stand v18.8-gui kopieren.

Fenstertitel:

LiveTranslate v18.10-prefix [develop]
