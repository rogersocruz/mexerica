@echo off
rem Roda o install.ps1 mesmo com o PowerShell bloqueando scripts (politica
rem de execucao "Restricted", o padrao do Windows). Aceita os mesmos
rem parametros: install.cmd -Converters -Office
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 pause
