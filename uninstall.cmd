@echo off
rem Roda o uninstall.ps1 mesmo com o PowerShell bloqueando scripts.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" %*
if errorlevel 1 pause
