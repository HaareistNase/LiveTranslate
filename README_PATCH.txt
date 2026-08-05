LiveTranslate v18.14-stable – Bewährte Serverparameter

Dieser Patch übernimmt den erfolgreichen Referenzlauf als integrierten
Standard.

Serverkonfiguration:

- Backend: faster-whisper
- Policy: simulstreaming
- Modell: large-v3
- Sprache: Auswahl aus der GUI; bei Automatisch = auto
- audio-max-len: 45 Sekunden
- buffer_trimming: segment
- buffer_trimming_sec: 15 Sekunden
- max-context-tokens: 0
- PCM-Eingang
- Log-Level INFO

Geändert:

- config.py
- server_manager.py
- version.py

Zusätzlich:

- stop_external_wlk.bat

Unverändert bleiben:

- main_gui.py
- wlk_stream.py
- transcript_assembler.py
- context_buffer.py
- NLLB
- Diagnose-Probes

Wichtig vor dem ersten Test:

Ein manuell gestarteter WLK-Server auf Port 8000 verwendet weiterhin
seine alten Startparameter. Deshalb alle WLK-Fenster schließen oder
stop_external_wlk.bat ausführen.

Danach nur noch die GUI starten. Sie startet WhisperLiveKit selbst mit
der neuen Standardkonfiguration.

Für das russische Referenzvideo in der GUI ausdrücklich "Russisch"
wählen. Das war Bestandteil des erfolgreichen Laufs.

Fenstertitel:

LiveTranslate v18.14-stable [develop]
