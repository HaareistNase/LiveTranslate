LiveTranslate v18.16-hallucination-guard

Gezielter Halluzinationsschutz für den beobachteten Fehler.

Geändert:

- hallucination_filter.py
- context_buffer.py
- wlk_stream.py
- version.py
- tests/test_hallucination_guard.py

Neu:

1. Russische Phrase "Продолжение следует" wird auch in verstümmelten
   und mehrfach wiederholten Schreibweisen erkannt.

2. Die Phrase wird aus gemischten Blöcken entfernt, ohne echten Text
   davor und danach zu verlieren.

3. Eine NLLB-Ausgabe wird nur verworfen, wenn sie gleichzeitig:
   - mindestens dreimal so viele Wörter wie der Quellblock enthält,
   - mindestens 18 Wörter lang ist,
   - und stark wiederholte Wörter oder Wortgruppen enthält.

Unverändert:

- GUI-Historie bleibt bei 50
- Serverparameter bleiben unverändert
- Tracker und Segmentierung bleiben unverändert
- normale längere Übersetzungen werden nicht gefiltert

Fenstertitel:

LiveTranslate v18.16-hallucination-guard [develop]
