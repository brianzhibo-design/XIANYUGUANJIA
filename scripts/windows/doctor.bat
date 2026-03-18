@echo off
setlocal

cd /d %~dp0\..\..

if not exist .venv\Scripts\python.exe (
  echo [ERROR] .venv not found. Run scripts\windows\setup_windows.bat first.
  exit /b 1
)

set STRICT=
set SKIP_QUOTE=

for %%A in (%*) do (
  if /I "%%~A"=="--strict" set STRICT=--strict
  if /I "%%~A"=="--skip-quote" set SKIP_QUOTE=--skip-quote
)

call .venv\Scripts\python -m src.cli doctor %STRICT% %SKIP_QUOTE%
exit /b %ERRORLEVEL%
