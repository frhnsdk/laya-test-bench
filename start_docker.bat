@echo off
rem Starts the Laya test bench in Docker (first run builds the image; later runs start in seconds).
cd /d "%~dp0"
docker info >nul 2>&1 || (echo Docker Desktop is not running. Start it and try again. & pause & exit /b 1)
set FILES=-f docker-compose.yml
nvidia-smi >nul 2>&1
if not errorlevel 1 set FILES=%FILES% -f docker-compose.gpu.yml
docker compose %FILES% up -d --build || (echo Build or start failed. & pause & exit /b 1)
echo Waiting for the server...
:wait
powershell -NoProfile -Command "try { (Invoke-RestMethod http://127.0.0.1:8000/api/status -TimeoutSec 3).ready } catch { 'no' }" | findstr /i "True" >nul || (ping -n 3 127.0.0.1 >nul & goto wait)
start "" http://127.0.0.1:8000
echo Running at http://127.0.0.1:8000  (stop it with stop_docker.bat)
