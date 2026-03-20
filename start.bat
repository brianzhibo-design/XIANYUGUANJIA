@echo off
REM 闲鱼管家 - Windows 启动（供 update.bat 一键更新后调用）
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

set "PORT=8091"
if not "%XIANYU_DASHBOARD_PORT%"=="" set "PORT=%XIANYU_DASHBOARD_PORT%"

echo [^>^>] 启动 Dashboard 端口 %PORT% ...
start "xianyu-dashboard" /MIN "%PY%" -m src.dashboard_server --port %PORT%

endlocal
exit /b 0
