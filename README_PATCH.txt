# LiveTranslate v18.1-dev – Patch

Dieser Patch enthält nur vier Dateien und überschreibt ausdrücklich
keine `.gitignore`.

## Behoben

Der ContextBuffer konnte bei durchgehender Sprache unbegrenzt offen
bleiben. Die bisherige Zeichengrenze zählte nur bereits abgeschlossene
Sätze, nicht aber den noch unpunktierten Resttext.

Dadurch konnte nach einigen sichtbaren Blöcken scheinbar keine weitere
Übersetzung mehr erscheinen.

Jetzt wird ein Block zusätzlich spätestens nach sechs Sekunden
ausgegeben, auch wenn keine Pause und kein Satzzeichen vorkommen.

## Versionsanzeige

Die GUI zeigt nun:

- Fenstertitel: `LiveTranslate v18.1-dev [develop]`
- Überschrift: `LiveTranslate v18.1-dev`
- Statuszeile beim Start: `v18.1-dev · develop · Bereit`

## Enthaltene Dateien

- `version.py`
- `config.py`
- `context_buffer.py`
- `main_gui.py`

Keine virtuellen Umgebungen, Modelle, ZIPs oder `.gitignore`.
