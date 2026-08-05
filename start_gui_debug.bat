@echo off
cd /d "%~dp0"

call "venv_wlk\Scripts\activate.bat"

python main_gui.py

pause
