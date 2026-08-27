@echo off
REM Double-click this file to run OMNIS. Works even if PowerShell's
REM ExecutionPolicy would otherwise block .ps1 scripts (the -ExecutionPolicy
REM Bypass flag below applies only to this one process, not your system).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update-and-run.ps1"
echo.
pause
