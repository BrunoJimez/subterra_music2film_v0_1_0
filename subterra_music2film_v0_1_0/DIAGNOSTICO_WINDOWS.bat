@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" subterra.py diagnose --output hardware_report.json
) else (
  py -3 subterra.py diagnose --output hardware_report.json
)
pause
