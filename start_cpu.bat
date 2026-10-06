@echo off
rem Laya test bench on the CPU (no GPU). Slower than start.bat. Close this window to stop the server.
cd /d "%~dp0"
set LAYA_DEVICE=cpu
start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" app.py
pause
