LiveTranslate v18.5-dev – Kontrollierter WhisperLiveKit-Drain

Beim Stoppen wird die Aufnahme nicht mehr abrupt beendet.

Ablauf:
1. Audioaufnahme anhalten.
2. Audioqueue vollständig senden.
3. Leeres PCM-Paket an WhisperLiveKit senden.
4. Auf `ready_to_stop` warten.
5. Letztes Wort und ContextBuffer freigeben.
6. Übersetzungsqueue vollständig abarbeiten.
7. Erst danach den Live-Text für den Referenzvergleich lesen.

Die stabile Wortausgabe aus v18.4.1 bleibt erhalten.

Keine .gitignore, keine Modelle, keine virtuellen Umgebungen.

Fenstertitel:
LiveTranslate v18.5-dev [develop]
