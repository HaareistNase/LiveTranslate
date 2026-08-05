# LiveTranslate Auto NLLB v11

Diese Version setzt die drei geplanten Qualitätsverbesserungen um.

## 1. Übersetzungen vorberechnen

Mehrere wartende Abschnitte werden gesammelt und gemeinsam als
GPU-Batch durch NLLB geschickt. Während WhisperLiveKit bereits den
nächsten Text erkennt, verarbeitet NLLB die vorherigen Abschnitte.

Einstellungen in `config.py`:

```python
TRANSLATION_BATCH_SIZE = 4
TRANSLATION_BATCH_WAIT_SECONDS = 0.20
```

## 2. Bessere Segmentierung

Unterstützt werden neben Punkt, Fragezeichen und Ausrufezeichen auch:

```text
。！？…
```

Kurze Fragmente werden nicht sofort einzeln übersetzt. Stattdessen
werden zusammengehörige Sätze bis zu einer sinnvollen Blockgröße
gesammelt. Bei einer Pause wird der verbleibende Text automatisch
ausgegeben.

## 3. Kontext über mehrere Sätze

Bis zu drei benachbarte bestätigte Sätze werden als gemeinsamer
Übersetzungsblock an NLLB geschickt. Dadurch sieht NLLB lokale
Zusammenhänge wie Pronomen, Satzanschlüsse und Dialogbezüge.

Einstellungen:

```python
SEGMENT_MAX_SENTENCES = 3
SEGMENT_MAX_CHARACTERS = 280
SEGMENT_FLUSH_SECONDS = 2.0
```

## Start

Zuerst:

```cmd
start_wlk_auto.bat
```

Danach:

```cmd
start_client.bat
```

Die funktionierende CUDA-PyTorch-Version wird durch die Installation
nicht verändert.
