@echo off
setlocal
echo Suche WhisperLiveKit auf Port 8000 ...

set "FOUND=0"

for /f "tokens=5" %%P in (
    'netstat -ano ^| findstr /R /C:":8000 .*LISTENING"'
) do (
    set "FOUND=1"
    echo Beende PID %%P ...
    taskkill /PID %%P /F
)

if "%FOUND%"=="0" (
    echo Kein Server auf Port 8000 gefunden.
)

pause
