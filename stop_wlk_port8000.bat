@echo off
setlocal
echo Suche Prozess auf Port 8000 ...

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
    echo Beende PID %%P ...
    taskkill /PID %%P /F
)

echo Fertig.
pause
