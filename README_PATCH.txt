LiveTranslate v18.7-dev – LiveLineTracker

Zwischenstände derselben Whisper-Zeile werden nicht mehr an NLLB
geschickt. Der jeweils aktuelle Stand ersetzt nur den vorherigen.

Eine vollständige Zeile wird ausgegeben bei:
- neuer Startzeit,
- 1,8 Sekunden Inaktivität,
- kontrolliertem Stopp,
- maximal 12 Sekunden als Sicherheitsgrenze.

Ziel:
- keine Wortfragmente,
- keine künstliche Trennung von Subjekt und Verb,
- keine Zwischenstand-Dopplungen,
- vollständige Satzblöcke für NLLB.

Enthalten:
- version.py
- config.py
- transcript_assembler.py
- wlk_stream.py
- tests/test_live_line_tracker.py

Keine .gitignore, keine Modelle, keine virtuellen Umgebungen.

Fenstertitel:
LiveTranslate v18.7-dev [develop]
