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
echo WhisperLiveKit TUNED - SimulStreaming Langzeit-Test
echo ============================================================
echo.
echo Geaenderte Serverparameter:
echo   audio-max-len       = 300 Sekunden
echo   buffer-trimming-sec = 300 Sekunden
echo   max-context-tokens  = 2048
echo.
echo Port 8000 muss frei sein.
echo.

wlk ^
  --backend faster-whisper ^
  --backend-policy simulstreaming ^
  --model large-v3 ^
  --language ru ^
  --audio-max-len 45 ^
  --buffer_trimming segment ^
  --buffer_trimming_sec 15 ^
  --max-context-tokens 0 ^
  --pcm-input ^
  --log-level INFO

set "EXITCODE=%ERRORLEVEL%"

echo.
echo WhisperLiveKit wurde beendet. Exitcode: %EXITCODE%
pause
exit /b %EXITCODE%
