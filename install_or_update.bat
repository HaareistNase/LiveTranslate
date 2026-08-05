@echo off
cd /d "%~dp0"

call "venv_wlk\Scripts\activate.bat"

echo Installiere Client-Abhaengigkeiten, ohne PyTorch zu veraendern ...
python -m pip install --upgrade -r requirements.txt

echo.
echo Pruefe die Umgebung ...
python -m pip check

pause
