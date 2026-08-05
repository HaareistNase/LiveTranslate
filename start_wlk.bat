@echo off
cd /d "%~dp0"

call "venv_wlk\Scripts\activate.bat"

set "TORCH_DLL_PATH=E:\KI\LiveTranslate\venv\Lib\site-packages\torch\lib"
set "PATH=%TORCH_DLL_PATH%;%PATH%"

echo CUDA-DLL-Ordner:
echo %TORCH_DLL_PATH%
echo.

where cublas64_12.dll
where cudnn64_9.dll
echo.

wlk --backend faster-whisper --backend-policy localagreement --model large-v3 --language ru --pcm-input

pause
