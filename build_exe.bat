@echo off
cd /d "%~dp0"

call "venv_wlk\Scripts\activate.bat"

python -m pip install --upgrade nuitka ordered-set zstandard

python -m nuitka ^
  --standalone ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --include-module=whisperlivekit ^
  --include-package=whisperlivekit ^
  --include-package=transformers ^
  --include-package=sentencepiece ^
  --include-package=ctranslate2 ^
  --include-package=torch ^
  --output-dir=build ^
  --output-filename=LiveTranslate.exe ^
  main_gui.py

pause
