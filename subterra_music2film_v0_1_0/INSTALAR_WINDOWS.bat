@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.11 ou 3.12 e marque Add Python to PATH.
  pause
  exit /b 1
)
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo AVISO: FFmpeg nao esta no PATH. Instale-o antes de renderizar.
) else (
  echo FFmpeg encontrado.
)
echo Instalacao concluida. Abra ABRIR_SUBTERRA.bat
pause
