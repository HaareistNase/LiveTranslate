LiveTranslate v18.11-pipeline-probe

Reiner Diagnosepatch. Es werden keine ASR-, Tracker-, Kontext-,
Übersetzungs- oder GUI-Entscheidungen verändert.

Enthalten:
- version.py
- wlk_stream.py
- pipeline_probe.py

Nicht enthalten und unverändert:
- transcript_assembler.py
- main_gui.py
- context_buffer.py
- config.py
- nllb_translator.py

Pro Sitzung entstehen:

logs\pipeline_probe\pipeline_probe_YYYYMMDD_HHMMSS.jsonl
logs\pipeline_probe\pipeline_summary_YYYYMMDD_HHMMSS.json

Protokollierte Übergänge:

1. websocket_packet
2. raw_item
3. tracker_output
4. context_input
5. context_output
6. translation_queue
7. nllb_input
8. nllb_output
9. gui_output

Test:
1. Über den aktuellen v18.10-prefix-Stand kopieren.
2. Referenzvideo 60 bis 90 Sekunden abspielen.
3. Stopp drücken und Offline-Auswertung abwarten.
4. Neueste pipeline_probe_*.jsonl und pipeline_summary_*.json hochladen.

Fenstertitel:
LiveTranslate v18.11-pipeline-probe [develop]
