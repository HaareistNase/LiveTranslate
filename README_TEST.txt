WhisperLiveKit SimulStreaming – A/B-Servertest
================================================

Dieses Paket überschreibt keine Python-Dateien und keine Konfiguration
von LiveTranslate.

Enthalten:
- start_wlk_simul_baseline.bat
- start_wlk_simul_tuned_300s.bat
- stop_wlk_port8000.bat

Testablauf
----------

1. LiveTranslate und alle alten WLK-Fenster schließen.

2. Optional:
   stop_wlk_port8000.bat
   ausführen, damit Port 8000 sicher frei ist.

3. Für den eigentlichen Test starten:
   start_wlk_simul_tuned_300s.bat

4. Das Serverfenster geöffnet lassen.

5. In einem zweiten Fenster die bestehende LiveTranslate-GUI starten.

6. Das Referenzvideo mindestens 90 Sekunden laufen lassen.

7. In LiveTranslate auf Stopp klicken und die Offline-Auswertung
   vollständig abwarten.

8. Hochladen:
   - reference_report_*.json
   - raw_websocket_summary_*.json
   - bei Auffälligkeiten zusätzlich raw_websocket_*.jsonl

Geänderte Serverparameter
-------------------------

--audio-max-len 300
--buffer_trimming segment
--buffer_trimming_sec 300
--max-context-tokens 2048

Diese Werte sind nur ein Diagnoseversuch. Die Kommandohilfe bestätigt,
dass die Parameter existieren. Sie beweist jedoch nicht, dass diese
konkreten Werte optimal sind.

Baseline
--------

start_wlk_simul_baseline.bat startet denselben Server ohne die drei
erweiterten Zahlenwerte. Damit ist später ein direkter A/B-Vergleich
möglich.

Wichtig
-------

Wenn WinError 10048 erscheint, läuft noch ein anderer Prozess auf
Port 8000. Dann stop_wlk_port8000.bat ausführen und erneut starten.
