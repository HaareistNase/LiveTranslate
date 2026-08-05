@echo off
cd /d "%~dp0"

call "venv_wlk\Scripts\activate.bat"

set "TORCH_DLL_PATH=E:\KI\LiveTranslate\venv\Lib\site-packages\torch\lib"
set "PATH=%TORCH_DLL_PATH%;%PATH%"

wlk ^
  --backend faster-whisper ^
  --backend-policy simulstreaming ^
  --model large-v3 ^
  --language auto ^
  --pcm-input

pause
