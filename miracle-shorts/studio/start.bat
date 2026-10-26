@echo off
rem Miracle Shorts Studio - double-click to start, close this window to stop.
rem Uses the first Python that has numpy + Pillow (PCs can have several Pythons; the newest one may lack them).
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
for %%P in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "py -3.12" "python" "py") do (
  if not defined PY (
    %%~P -c "import numpy, PIL" >nul 2>&1 && set "PY=%%~P"
  )
)
if not defined PY (
  echo.
  echo [!] numpy / Pillow 가 설치된 Python 을 찾지 못했어요.
  echo     명령 프롬프트에서:  python -m pip install numpy pillow
  echo.
  pause
  exit /b 1
)
echo Python: %PY%
%PY% server.py
pause
