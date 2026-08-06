# LiveTranslate GUI v17.3 – Pipeline-Diagnose

Diese Version soll den Duplikatfehler noch nicht mit einer weiteren
Heuristik verdecken. Sie protokolliert stattdessen jede Stufe der
Verarbeitung.

## Protokollierte Stufen

- `RAW_WEBSOCKET` – vollständiges WhisperLiveKit-Paket
- `RAW_ITEMS` – die darin enthaltenen bestätigten Zeilen
- `ASSEMBLER_RAW_ITEM` – Eingang des TranscriptAssemblers
- `ASSEMBLER_OUTPUT` – ermittelter neuer Text
- `ASSEMBLER_SKIPPED` – verworfener Text
- `CONTEXT_INPUT` – Eingang des ContextBuffers
- `CONTEXT_PARTIAL` – angesammelter Text
- `CONTEXT_BLOCKS` / `CONTEXT_FLUSH` – an NLLB übergebene Blöcke
- `QUEUE_SEGMENT` – Eintrag in der Übersetzungswarteschlange
- `NLLB_INPUT_BATCH` – tatsächlicher Originaltext für NLLB
- `NLLB_OUTPUT_BATCH` – NLLB-Ergebnis
- `GUI_SUBTITLE` – Text, der an die GUI geschickt wird

## Testablauf

1. Auf dem Branch `develop` installieren.
2. `start_gui_debug.bat` starten.
3. Debugmodus in der GUI aktivieren.
4. Nur etwa 20 bis 30 Sekunden des problematischen Videos abspielen.
5. Anwendung mit `Stopp` beenden.
6. Diese Datei öffnen:

```text
logs\pipeline_debug.log
```

Die Datei enthält den vollständigen Ablauf und wird bei jedem Start
neu angelegt.

## Wichtig

Bitte nicht mehrere Minuten testen. Das vollständige WebSocket-Protokoll
kann schnell groß werden.

Nach dem Test genügt es, `pipeline_debug.log` hier hochzuladen.


## v18 – Duplikatursache behoben

WhisperLiveKit liefert eine laufende Zeile mehrfach mit demselben
Startzeitpunkt, aber einer ständig wachsenden Endzeit.

Die alte Identität war:

```text
speaker + start + end
```

Damit wurde jede Erweiterung als neue Zeile behandelt.

Die neue Identität ist:

```text
speaker + start
```

Dadurch erkennt der TranscriptAssembler dieselbe wachsende Zeile wieder
und gibt nur den neu hinzugekommenen Text an den ContextBuffer weiter.

Beispiel:

```text
Alt: Казалось, ребенку бежать
Neu: Казалось, ребенку бежать и даже
Ausgabe: и даже
```

Die Pipeline-Diagnose bleibt im Projekt vorhanden, ist aber standardmäßig
deaktiviert.
