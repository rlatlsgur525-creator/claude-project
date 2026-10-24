@echo off
rem Miracle Shorts Studio - double-click to start, close this window to stop.
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" server.py
pause
