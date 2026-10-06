@echo off
rem Laya test bench: double-click to start. Close this window to stop the server.
cd /d "%~dp0"
start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" app.py
pause
