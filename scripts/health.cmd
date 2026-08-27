@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0health.ps1"
echo.
pause
