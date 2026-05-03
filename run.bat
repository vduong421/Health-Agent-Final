@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\_shared_project_workbench\bootstrap_project_workbench.ps1" -ProjectDir "%~dp0"
if errorlevel 1 (
  echo.
  echo Workbench launch failed.
  pause
)
endlocal

