LiveTranslate v18.4-dev – Stabile Wortausgabe

Behoben:
Die Live-Transkription zerlegte russische Wörter, weil bei jeder
Whisper-Erweiterung sofort der reine Zeichensuffix ausgegeben wurde.

Beispiele:
- Андрей -> Анд рей
- русский -> рус ский
- живу -> Ж ив у
- Сибири -> С иб ири

Neue Logik:
- Das letzte Wort einer wachsenden Zeile wird zurückgehalten.
- Erst beim Beginn eines weiteren Wortes gilt es als stabil.
- Beim Zeilenwechsel wird der Rest ausgegeben.
- Nach 1,2 Sekunden ohne Aktualisierung wird die Zeile abgeschlossen.
- Beim Stoppen wird sämtlicher Resttext ausgegeben.

Enthalten:
- version.py
- transcript_assembler.py
- wlk_stream.py
- tests/test_transcript_word_stability.py

Keine .gitignore, keine Modelle, keine virtuellen Umgebungen.

Erwarteter Fenstertitel:
LiveTranslate v18.4-dev [develop]
