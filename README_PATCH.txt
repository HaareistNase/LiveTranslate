LiveTranslate v18.4.1-dev – Hotfix auf korrekter Basis

Wichtig:
Dieser Patch basiert ausdrücklich auf v18.3.1-dev und behält den
funktionierenden Konstruktorparameter `reference_capture`.

Behoben:
- Kein Fehler mehr:
  WLKStream.__init__() got an unexpected keyword argument
  'reference_capture'
- Russische Wörter werden nicht mehr als Zeichensuffixe zerlegt.
- Das letzte potenziell unfertige Wort wird zurückgehalten.
- Bei Pause, Zeilenwechsel oder Stopp wird der Rest ausgegeben.

Enthalten:
- version.py
- transcript_assembler.py
- wlk_stream.py
- main_gui.py
- config.py
- reference_benchmark.py
- tests/test_transcript_word_stability.py

Keine .gitignore, keine Modelle, keine virtuellen Umgebungen.

Erwarteter Fenstertitel:
LiveTranslate v18.4.1-dev [develop]
