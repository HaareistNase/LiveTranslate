LiveTranslate v18.6-dev – Robustheits-Patch

Ziele:
- Systemton mit sichtbarem RMS muss zuverlässig bei Whisper ankommen.
- Leise Videos werden automatisch angehoben.
- Verzögerte Spracherkennung darf keinen Text verlieren.
- Unbekannte Sprachcodes dürfen niemals zum Absturz führen.
- Kurzzeitige WebSocket-Probleme werden automatisch neu verbunden.

Neu:

1. Adaptive Audio-Verstärkung
   Ziel-RMS 0.035, maximal 12-fache Verstärkung, mit Limiter.

2. Audio-Status getrennt von ASR
   Ein sichtbarer RMS-Ausschlag wird nicht mehr als
   "kein Systemton" bezeichnet. Stattdessen:
   "Systemton vorhanden · warte auf Spracherkennung …"

3. Text-Zwischenspeicher
   Solange Auto-Erkennung noch keine unterstützte Sprache liefert,
   werden bis zu 32 Kontextblöcke gepuffert und später übersetzt.

4. Sprachcode-Normalisierung
   Beispiele: rus -> ru, jpn -> ja, zh-CN -> zh.

5. Unbekannte Sprache
   Führt nur zu:
   "Sprache 'xx' erkannt, aber nicht konfiguriert"
   Die Audio- und ASR-Verarbeitung läuft weiter.

6. WebSocket-Retry
   Bis zu 8 automatische Verbindungsversuche.

Enthalten:
- version.py
- config.py
- wlk_stream.py
- main_gui.py
- übrige Dateien aus der funktionierenden v18.5-Basis

Keine .gitignore, keine Modelle, keine virtuellen Umgebungen.

Erwarteter Fenstertitel:
LiveTranslate v18.6-dev [develop]
