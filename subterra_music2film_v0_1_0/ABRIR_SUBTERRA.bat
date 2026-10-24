@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado. Execute INSTALAR_WINDOWS.bat primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" gui.py
if errorlevel 1 pause
