@echo off
setlocal
cd /d "%~dp0"
echo Edite este arquivo e substitua CAMINHO_DA_MUSICA.wav.
".venv\Scripts\python.exe" subterra.py render "CAMINHO_DA_MUSICA.wav" "output\filme.mp4" --resolution 1080p --render-scale 0.75 --style auto
pause
