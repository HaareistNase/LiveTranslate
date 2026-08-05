@echo off
setlocal
cd /d "%~dp0"

if not exist "venv_wlk\Scripts\activate.bat" (
    echo FEHLER: venv_wlk wurde nicht gefunden.
    pause
    exit /b 1
)

call "venv_wlk\Scripts\activate.bat"

set "TORCH_DLL_PATH=%~dp0venv\Lib\site-packages\torch\lib"
if exist "%TORCH_DLL_PATH%" (
    set "PATH=%TORCH_DLL_PATH%;%PATH%"
)

echo.
echo ============================================================
echo WhisperLiveKit BASELINE - SimulStreaming
echo ============================================================
echo.
echo Port 8000 muss frei sein.
echo.

wlk ^
  --backend faster-whisper ^
  --backend-policy simulstreaming ^
  --model large-v3 ^
  --language auto ^
  --buffer_trimming segment ^
  --pcm-input ^
  --log-level INFO

set "EXITCODE=%ERRORLEVEL%"

echo.
echo WhisperLiveKit wurde beendet. Exitcode: %EXITCODE%
pause
exit /b %EXITCODE%
