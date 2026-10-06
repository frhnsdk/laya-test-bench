@echo off
rem Laya test bench launcher. Double-click to start (or restart) it; the page opens in your browser.
rem Needs: Docker Desktop running, and laya-testbench.tar next to this file (first run only).
rem Optional env vars: LAYA_NAME (container name, default laya), LAYA_PORT (default 8000), NO_BROWSER=1
setlocal
cd /d "%~dp0"
if not defined LAYA_NAME set LAYA_NAME=laya
if not defined LAYA_PORT set LAYA_PORT=8000

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start it, wait until it says "Engine running", then run this again.
  pause & exit /b 1
)

rem 1) Load the image the first time (about 5 GB, takes a few minutes).
docker image inspect laya-testbench >nul 2>&1
if errorlevel 1 (
  set TAR=
  if exist "laya-testbench.tar" set TAR=laya-testbench.tar
  if not defined TAR if exist "..\laya-testbench.tar" set TAR=..\laya-testbench.tar
  if not defined TAR (
    echo Image "laya-testbench" is not loaded and laya-testbench.tar was not found next to this file.
    echo Put laya-testbench.tar in this folder and run again. See README.md.
    pause & exit /b 1
  )
  echo Loading the image from %TAR% - this takes a few minutes, once...
  docker load -i "%TAR%" || (echo Loading failed. See README.md, Troubleshooting. & pause & exit /b 1)
)

rem 2) Start the container: reuse it if it exists, otherwise create it (with the GPU when possible).
docker container inspect %LAYA_NAME% >nul 2>&1
if not errorlevel 1 (
  echo Starting existing container "%LAYA_NAME%"...
  docker start %LAYA_NAME% >nul || (echo Could not start it. See README.md, Troubleshooting. & pause & exit /b 1)
  goto wait
)

if not exist "data" mkdir "data"
echo Creating container "%LAYA_NAME%" with GPU...
docker run -d --name %LAYA_NAME% -p 127.0.0.1:%LAYA_PORT%:8000 --restart unless-stopped --gpus all -v "%~dp0data:/app/data" laya-testbench >nul 2>&1
if errorlevel 1 (
  echo No usable GPU support found - creating it on the CPU instead. It works, just slower for big CSV files.
  docker container inspect %LAYA_NAME% >nul 2>&1
  if errorlevel 1 (
    docker run -d --name %LAYA_NAME% -p 127.0.0.1:%LAYA_PORT%:8000 --restart unless-stopped -v "%~dp0data:/app/data" laya-testbench >nul || (echo Could not create the container. See README.md, Troubleshooting. & pause & exit /b 1)
  ) else (
    echo A leftover container from the failed GPU attempt exists; starting it on the CPU is not possible. See README.md, Troubleshooting.
    pause & exit /b 1
  )
)

:wait
echo Waiting for the server (about 10 seconds)...
set /a tries=0
:poll
powershell -NoProfile -Command "try { (Invoke-RestMethod http://127.0.0.1:%LAYA_PORT%/api/status -TimeoutSec 3).ready } catch { 'no' }" | findstr /i "True" >nul
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% geq 45 (echo The server did not become ready. Run: docker logs %LAYA_NAME% & pause & exit /b 1)
ping -n 3 127.0.0.1 >nul
goto poll

:ready
if not defined NO_BROWSER start "" http://127.0.0.1:%LAYA_PORT%
echo.
echo Laya test bench is running at http://127.0.0.1:%LAYA_PORT%
echo Feedback you give with the thumbs buttons is saved in the "data" folder next to this file.
echo Stop it with stop.bat (or the stop button in Docker Desktop).
endlocal
