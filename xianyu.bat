@echo off
:: 先保存当前代码页，然后设置UTF-8
for /f "tokens=2 delims=:" %%a in ('chcp') do set "OLD_CP=%%a"
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ========================================
:: 闲鱼自动化 - 独立运行版入口
:: 完全脱离Docker和OpenClaw Gateway
:: ========================================

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: 如果没有参数，显示交互式菜单
if "%~1"=="" goto :WELCOME

:: 解析命令
set "COMMAND=%~1"
shift

if /I "!COMMAND!"=="setup" goto :SETUP
if /I "!COMMAND!"=="install" goto :SETUP
if /I "!COMMAND!"=="config" goto :CONFIG
if /I "!COMMAND!"=="start" goto :START
if /I "!COMMAND!"=="stop" goto :STOP
if /I "!COMMAND!"=="restart" goto :RESTART
if /I "!COMMAND!"=="status" goto :STATUS
if /I "!COMMAND!"=="logs" goto :LOGS
if /I "!COMMAND!"=="doctor" goto :DOCTOR
if /I "!COMMAND!"=="menu" goto :MENU
if /I "!COMMAND!"=="dashboard" goto :DASHBOARD
if /I "!COMMAND!"=="presales" goto :START_PRESALES
if /I "!COMMAND!"=="operations" goto :START_OPERATIONS
if /I "!COMMAND!"=="aftersales" goto :START_AFTERSALES

goto :HELP

:: ========================================
:: 命令实现
:: ========================================

:WELCOME
cls
echo.
echo ===========================================
echo    闲鱼自动化 - Windows独立版
echo ===========================================
echo.
echo 欢迎使用！请选择操作：
echo.
echo  [1] 首次部署 - 初始化环境
echo  [2] 配置向导 - 设置AI Key和Cookie
echo  [3] 启动服务 - 运行自动化模块
echo  [4] 管理菜单 - 查看状态/日志/停止
echo  [5] 帮助信息 - 查看所有命令
echo  [0] 退出
echo.
echo ===========================================
set /p choice="请输入选项 (0-5): "

if "!choice!"=="1" goto :SETUP
if "!choice!"=="2" goto :CONFIG
if "!choice!"=="3" goto :START_MENU
if "!choice!"=="4" goto :MENU
if "!choice!"=="5" goto :HELP
if "!choice!"=="0" exit /b 0
goto :WELCOME

:START_MENU
cls
echo.
echo ===========================================
echo    启动服务
echo ===========================================
echo.
echo  [1] 启动所有模块（售前+运营+售后）
echo  [2] 仅启动售前模块（自动回复）
echo  [3] 仅启动运营模块（擦亮/改价）
echo  [4] 仅启动售后模块（发货处理）
echo  [0] 返回主菜单
echo.
set /p start_choice="请输入选项 (0-4): "

if "!start_choice!"=="1" (
    call scripts\windows\start_module.bat presales daemon
    call scripts\windows\start_module.bat operations daemon
    call scripts\windows\start_module.bat aftersales daemon
    pause
)
if "!start_choice!"=="2" call scripts\windows\start_module.bat presales daemon ^& pause
if "!start_choice!"=="3" call scripts\windows\start_module.bat operations daemon ^& pause
if "!start_choice!"=="4" call scripts\windows\start_module.bat aftersales daemon ^& pause
if "!start_choice!"=="0" goto :WELCOME
goto :WELCOME

:HELP
echo.
echo ===========================================
echo    闲鱼自动化 - 命令行工具
echo ===========================================
echo.
echo 用法: xianyu [命令] [选项]
echo.
echo 部署命令:
echo   setup, install    初始化环境（首次运行）
echo   config            运行配置向导
echo.
echo 模块命令:
echo   start [模块]      启动模块（presales/operations/aftersales/all）
echo   stop [模块]       停止模块
echo   restart [模块]    重启模块
echo   presales          快捷启动售前模块
echo   operations        快捷启动运营模块
echo   aftersales        快捷启动售后模块
echo.
echo 管理命令:
echo   status            查看运行状态
echo   logs [模块]       查看日志
echo   doctor            系统诊断
echo   menu              打开交互菜单
echo   dashboard         启动网页管理面板
echo.
echo 示例:
echo   xianyu setup                    # 首次部署
echo   xianyu start all                # 启动所有模块
echo   xianyu start presales           # 仅启动售前
echo   xianyu status                   # 查看状态
echo   xianyu logs presales            # 查看售前日志
echo.
pause
goto :WELCOME

:SETUP
call scripts\windows\install.bat
exit /b %ERRORLEVEL%

:CONFIG
call scripts\windows\simple_config.bat
exit /b %ERRORLEVEL%

:START
set "MODULE=%~1"
if "!MODULE!"=="" set "MODULE=all"
if /I "!MODULE!"=="all" (
    echo [*] 启动所有模块...
    call scripts\windows\start_module.bat presales daemon
    call scripts\windows\start_module.bat operations daemon
    call scripts\windows\start_module.bat aftersales daemon
) else (
    call scripts\windows\start_module.bat !MODULE! daemon
)
exit /b %ERRORLEVEL%

:START_PRESALES
call scripts\windows\start_module.bat presales daemon
exit /b %ERRORLEVEL%

:START_OPERATIONS
call scripts\windows\start_module.bat operations daemon
exit /b %ERRORLEVEL%

:START_AFTERSALES
call scripts\windows\start_module.bat aftersales daemon
exit /b %ERRORLEVEL%

:STOP
set "MODULE=%~1"
if "!MODULE!"=="" set "MODULE=all"
call scripts\windows\stop_module.bat !MODULE!
exit /b %ERRORLEVEL%

:RESTART
set "MODULE=%~1"
if "!MODULE!"=="" set "MODULE=all"
call scripts\windows\stop_module.bat !MODULE!
timeout /t 2 /nobreak >nul
call :START !MODULE!
exit /b %ERRORLEVEL%

:STATUS
call scripts\windows\status.bat
exit /b %ERRORLEVEL%

:LOGS
set "MODULE=%~1"
call scripts\windows\view_logs.bat !MODULE!
exit /b %ERRORLEVEL%

:DOCTOR
.venv\Scripts\python -m src.cli doctor --strict
pause
exit /b %ERRORLEVEL%

:MENU
call scripts\windows\menu.bat
exit /b %ERRORLEVEL%

:DASHBOARD
echo [*] 启动Dashboard...
echo    访问地址: http://localhost:8091
echo    按Ctrl+C停止
echo.
start "" http://localhost:8091
.venv\Scripts\python -m src.dashboard_server --port 8091
exit /b %ERRORLEVEL%
