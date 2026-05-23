@echo off
setlocal
set "ROOT=%~dp0"
if exist "%ROOT%.venv\Scripts\python.exe" (
  set "PYTHON=%ROOT%.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

if /I "%~1"=="detect" (
  "%PYTHON%" "%ROOT%detect.py" %2 %3 %4 %5 %6 %7 %8 %9
  exit /b %ERRORLEVEL%
)
if /I "%~1"=="see" (
  "%PYTHON%" "%ROOT%see.py" %2 %3 %4 %5 %6 %7 %8 %9
  exit /b %ERRORLEVEL%
)
if /I "%~1"=="chat" (
  "%PYTHON%" "%ROOT%chat.py" %2 %3 %4 %5 %6 %7 %8 %9
  exit /b %ERRORLEVEL%
)
if "%~1"=="" (
  "%PYTHON%" "%ROOT%chat.py"
  exit /b %ERRORLEVEL%
)

echo Usage: arif [chat] ^| arif detect ^| arif see
exit /b 1
