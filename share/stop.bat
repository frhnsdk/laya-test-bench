@echo off
rem Stops the Laya test bench. Run run.bat to start it again (nothing is lost or re-downloaded).
if not defined LAYA_NAME set LAYA_NAME=laya
docker stop %LAYA_NAME%
