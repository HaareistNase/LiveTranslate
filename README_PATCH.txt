LiveTranslate v18.17-dynamic-segments

Dynamische, lesbarere Übersetzungsblöcke.

Geändert:

- context_buffer.py
- config.py
- version.py
- tests/test_dynamic_segments.py

Neue Standardwerte:

- Zielgröße: 220 Zeichen
- mindestens 2 vollständige Sätze für die Zielausgabe
- maximal 6 Sätze
- maximal 420 Zeichen
- maximale Wartezeit: 4 Sekunden
- Pausenabschluss: 2,5 Sekunden

Verhalten:

- Kurze Sätze werden bevorzugt zusammengefasst.
- Ein unvollständiger Satz bleibt nach Möglichkeit im Puffer.
- Mitten im Satz wird nur ausgegeben, wenn kein Satzende kommt und der
  Text sonst dauerhaft hängen würde.
- Beim Stoppen wird der gesamte Rest ausgegeben.

Unverändert:

- Serverparameter aus v18.14-stable
- GUI-Historie mit 50 Einträgen
- Halluzinationsschutz aus v18.16
- Tracker
- Audio
- WhisperLiveKit
- NLLB

Fenstertitel:

LiveTranslate v18.17-dynamic-segments [develop]
