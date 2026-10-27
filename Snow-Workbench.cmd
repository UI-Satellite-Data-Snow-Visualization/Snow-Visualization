@echo off
title Snow Workbench
cd /d "%~dp0api"
if errorlevel 1 goto failed
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m jobs.tui
) else if exist "..\demo\.venv\Scripts\python.exe" (
  "..\demo\.venv\Scripts\python.exe" -m jobs.tui
) else (
  python -m jobs.tui
)
if errorlevel 1 goto failed
echo.
echo Snow Workbench closed.
pause
exit /b 0
:failed
echo.
echo Snow Workbench could not start. Keep this window open to read the error above.
echo Setup instructions are in api\README.md.
pause
exit /b 1