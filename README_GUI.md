# LiveTranslate GUI v16

Diese Version basiert wieder auf der funktionierenden GUI v14.

Die fehlerhafte Vorschau-/Revisionslogik aus v15 wurde vollständig
entfernt.

## Was geändert wurde

- Sprachwahl funktioniert wieder wie in v14.
- Start und Stopp funktionieren wieder wie in v14.
- Automatische Sprache oder feste Sprache bleiben auswählbar.
- Übersetzung startet wieder über die bewährte v14-Pipeline.
- Bis zu drei bestätigte Sätze werden gemeinsam übersetzt.
- Nach 2,5 Sekunden Pause wird der verbliebene Text ausgegeben.
- Keine laufenden Kontextrevisionen und keine komplizierte Vorschau.
- Kein sichtbares CMD-Fenster beim normalen Start.
- Ein separater Debug-Start mit Konsole bleibt verfügbar.
- Wiederkehrende Transformers-Warnungen werden unterdrückt.

## Normaler Start

```cmd
start_gui.bat
```

Das Programm startet ohne sichtbares CMD-Fenster.

## Debug-Start

```cmd
start_gui_debug.bat
```

Hier bleibt die Konsole sichtbar.

## Kontextwerte

```python
CONTEXT_MAX_SENTENCES = 3
CONTEXT_MAX_CHARACTERS = 420
CONTEXT_FLUSH_SECONDS = 2.5
```

Diese Variante ist bewusst konservativ: mehr Kontext als v14, aber
ohne die instabile Live-Neuübersetzung aus v15.
