@echo off
cd /d "%~dp0"
if exist "%~dp0..\..\work\organizer-venv\Scripts\pythonw.exe" (
  start "" "%~dp0..\..\work\organizer-venv\Scripts\pythonw.exe" -m organizer
) else (
  echo The workspace Python environment is missing. See README.md for setup.
  pause
)
