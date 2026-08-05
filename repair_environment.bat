@echo off
cd /d "%~dp0"

call "venv_wlk\Scripts\activate.bat"

echo Repariere NumPy und den CUDA-faehigen PyTorch-Stack ...
echo.

python -m pip uninstall -y torch torchvision torchaudio numpy

python -m pip install numpy==2.4.6

python -m pip install ^
  torch==2.8.0 ^
  torchvision==0.23.0 ^
  torchaudio==2.8.0 ^
  --index-url https://download.pytorch.org/whl/cu129

echo.
echo Pruefe PyTorch und CUDA ...
python -c "import torch; print('Torch:', torch.__version__); print('CUDA:', torch.version.cuda); print('CUDA verfuegbar:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'keine')"

echo.
echo Pruefe Paketabhaengigkeiten ...
python -m pip check

pause
