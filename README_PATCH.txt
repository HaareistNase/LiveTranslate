LiveTranslate v18.3-dev – Offline-Referenzvergleich

Enthalten:
- version.py
- config.py
- main_gui.py
- wlk_stream.py
- reference_benchmark.py

Keine .gitignore, keine Modelle, keine virtuellen Umgebungen.

Test mit dem Referenzvideo:
https://www.youtube.com/watch?v=JeRb7Ud1kSU

Ablauf:
1. GUI starten.
2. Quellsprache passend wählen oder Automatisch lassen.
3. "Offline-Referenzvergleich" aktivieren.
4. Start drücken.
5. Einen klar abgegrenzten Abschnitt des Videos abspielen, z. B. 60 Sekunden.
6. Video pausieren.
7. Stopp drücken.
8. Die App transkribiert exakt die aufgezeichnete Audiospur noch einmal
   offline mit faster-whisper large-v3.
9. Danach zeigt die GUI:
   - Wort- und Zeichenzahl der Live-Erkennung
   - Wort- und Zeichenzahl der Offline-Referenz
   - prozentuale Abdeckung

Berichte liegen unter:
logs\reference\

Wichtig:
Die Offline-Auswertung startet erst nach Stopp und kann je nach Länge
etwas dauern. Sie verwendet die RTX-GPU.
