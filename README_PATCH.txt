LiveTranslate v18.9-asr – Reines ASR-Feintuning

Geändert werden ausschließlich:
- config.py
- version.py

Unverändert bleiben:
- main_gui.py
- wlk_stream.py
- transcript_assembler.py
- context_buffer.py
- Audio- und Übersetzungslogik

Änderungen:
- ASR_LINE_STALE_SECONDS: 1.8 -> 2.4 Sekunden
- ASR_LINE_MAX_SECONDS: 12.0 -> 15.0 Sekunden

Ziel:
Kurze Sprechpausen sollen eine laufende Whisper-Zeile nicht zu früh
abschließen. Dadurch erhält NLLB häufiger vollständigere Satzteile.

Erwartete Nebenwirkung:
Neue Übersetzungen können etwa 0,6 Sekunden später erscheinen.

Diesen Patch über den funktionierenden Stand v18.8-gui kopieren.

Fenstertitel:
LiveTranslate v18.9-asr [develop]
