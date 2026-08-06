LiveTranslate v18.18-subtitle-postprocess

Optionale, vorsichtige Nachbearbeitung zwischen NLLB und GUI.

Geändert:

- wlk_stream.py
- version.py

Neu:

- subtitle_postprocessor.py
- tests/test_subtitle_postprocessor.py

Funktionen:

- Leerzeichen vor und nach Satzzeichen bereinigen
- direkt benachbarte identische Sätze entfernen
- extrem kurze unvollständige Fragmente mit höchstens zwei Wörtern
  beziehungsweise 18 Zeichen zurückhalten
- zurückgehaltene Fragmente mit dem nächsten deutschen Block verbinden
- beim Stoppen verbleibende Fragmente trotzdem anzeigen

Beispiel:

"Wälder"
+
"und verschneite Wege sehen wunderschön aus."

wird zu:

"Wälder und verschneite Wege sehen wunderschön aus."

Unverändert bleiben:

- WhisperLiveKit und Serverparameter
- Tracker
- ContextBuffer und dynamische Segmentbildung aus v18.17
- NLLB
- GUI und Historie
- Halluzinationsschutz

Hinweis:

Ein Fragment am absoluten Ende der Aufnahme kann nicht sinnvoll mit
einem Folgesatz verbunden werden. Es wird beim Stoppen deshalb
unverändert ausgegeben, damit kein Inhalt verloren geht.

Fenstertitel:

LiveTranslate v18.18-subtitle-postprocess [develop]
