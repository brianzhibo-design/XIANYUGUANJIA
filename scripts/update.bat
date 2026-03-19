@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM 闲鱼管家 - 在线更新脚本 (Windows)
REM 用法: scripts\update.bat <update-package.tar.gz> [project-root]

set "PACKAGE_PATH=%~1"
set "PROJECT_ROOT=%~2"
if "%PROJECT_ROOT%"=="" set "PROJECT_ROOT=%~dp0.."

set "STATUS_FILE=%PROJECT_ROOT%\data\update-status.json"

if "%PACKAGE_PATH%"=="" (
    echo [ERR] 用法: scripts\update.bat ^<update-package.tar.gz^> [project-root]
    exit /b 1
)

if not exist "%PACKAGE_PATH%" (
    echo [ERR] 更新包不存在: %PACKAGE_PATH%
    call :write_status "error" "更新包不存在"
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
if not exist "logs" mkdir logs
if not exist "data\backups" mkdir "data\backups"

echo [^>^>] =========================================
echo [^>^>] 闲鱼管家 · 在线更新
echo [^>^>] =========================================
echo [^>^>] 更新包: %PACKAGE_PATH%
echo [^>^>] 项目目录: %PROJECT_ROOT%
echo.

REM ═══════════════ 1. 备份 ═══════════════
echo [^>^>] [1/5] 创建备份...
call :write_status "backing_up" ""

set "TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\data\backups\pre-update-%TIMESTAMP%"

if exist "src" (
    xcopy /E /I /Q /Y "src" "%BACKUP_DIR%\src" >nul 2>&1
)
if exist "scripts" (
    xcopy /E /I /Q /Y "scripts" "%BACKUP_DIR%\scripts" >nul 2>&1
)
if exist "client\dist" (
    xcopy /E /I /Q /Y "client\dist" "%BACKUP_DIR%\client\dist" >nul 2>&1
)
if exist "requirements.txt" (
    copy /Y "requirements.txt" "%BACKUP_DIR%\" >nul 2>&1
)
echo [OK] 备份完成: data\backups\pre-update-%TIMESTAMP%

REM Keep only the 3 most recent backups
set "_BACKUP_COUNT=0"
for /f "delims=" %%B in ('dir /b /o-d "%PROJECT_ROOT%\data\backups\pre-update-*" 2^>nul') do (
    set /a "_BACKUP_COUNT+=1"
    if !_BACKUP_COUNT! gtr 3 (
        rmdir /S /Q "%PROJECT_ROOT%\data\backups\%%B" 2>nul
        del /F /Q "%PROJECT_ROOT%\data\backups\%%B" 2>nul
    )
)

REM ═══════════════ 2. 停止服务 ═══════════════
echo [^>^>] [2/5] 停止运行中的服务...
call :write_status "stopping" ""

REM Graceful: first try without /F, then force after wait
for %%P in (8091 5173) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING" 2^>nul') do (
        taskkill /PID %%A >nul 2>&1
        echo [OK] 已向端口 %%P PID %%A 发送停止信号
    )
)
timeout /t 3 /nobreak >nul
for %%P in (8091 5173) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING" 2^>nul') do (
        taskkill /F /PID %%A >nul 2>&1
        echo [!!] 端口 %%P PID %%A 强制终止
    )
)
timeout /t 1 /nobreak >nul

REM ═══════════════ 3. 解压覆盖 ═══════════════
echo [^>^>] [3/5] 解压并覆盖源码...
call :write_status "extracting" ""

set "TEMP_UPDATE=%TEMP%\xianyu-update-extract"
if exist "%TEMP_UPDATE%" rmdir /S /Q "%TEMP_UPDATE%"
mkdir "%TEMP_UPDATE%"

tar xzf "%PACKAGE_PATH%" -C "%TEMP_UPDATE%" 2>nul
if errorlevel 1 (
    echo [ERR] 解压失败
    goto :rollback
)

REM Find extracted directory
set "EXTRACTED_DIR="
for /d %%D in ("%TEMP_UPDATE%\*") do (
    set "EXTRACTED_DIR=%%D"
    goto :found_dir
)
:found_dir
if "%EXTRACTED_DIR%"=="" set "EXTRACTED_DIR=%TEMP_UPDATE%"

REM Overwrite source files
for %%I in (src scripts client) do (
    if exist "%EXTRACTED_DIR%\%%I" (
        if exist "%PROJECT_ROOT%\%%I" rmdir /S /Q "%PROJECT_ROOT%\%%I" 2>nul
        xcopy /E /I /Q /Y "%EXTRACTED_DIR%\%%I" "%PROJECT_ROOT%\%%I" >nul 2>&1
    )
)
for %%F in (requirements.txt start.sh start.bat quick-start.sh quick-start.bat) do (
    if exist "%EXTRACTED_DIR%\%%F" (
        copy /Y "%EXTRACTED_DIR%\%%F" "%PROJECT_ROOT%\%%F" >nul 2>&1
    )
)

echo [OK] 源码覆盖完成
rmdir /S /Q "%TEMP_UPDATE%" 2>nul

REM ═══════════════ 4. 更新依赖 ═══════════════
echo [^>^>] [4/5] 检查依赖更新...
call :write_status "installing_deps" ""

set "VENV_PIP="
if exist "%PROJECT_ROOT%\.venv\Scripts\pip.exe" set "VENV_PIP=%PROJECT_ROOT%\.venv\Scripts\pip.exe"

if not "%VENV_PIP%"=="" (
    if exist "%PROJECT_ROOT%\requirements.txt" (
        echo [^>^>] 安装依赖...
        "%VENV_PIP%" install -r "%PROJECT_ROOT%\requirements.txt" -q 2>&1
        echo [OK] 依赖安装完成
    )
) else (
    echo [!!] 未找到 venv pip，跳过依赖安装
)

REM ═══════════════ 4.5 配置迁移 ═══════════════
set "_CFG=%PROJECT_ROOT%\config\config.yaml"
if exist "%_CFG%" (
    findstr /C:"safety_margin: 0.03" "%_CFG%" >nul 2>&1
    if !errorlevel! equ 0 (
        powershell -Command "(Get-Content '%_CFG%') -replace 'safety_margin: 0\.03','safety_margin: 0.0' | Set-Content '%_CFG%'"
        echo [OK] 已自动将 safety_margin 从 0.03 修正为 0.0
    )
)

REM ═══════════════ 5. 重启服务 ═══════════════
echo [^>^>] [5/5] 重新启动服务...
call :write_status "restarting" ""

cd /d "%PROJECT_ROOT%"
if exist "start.bat" (
    start "" cmd /c "start.bat"
    echo [OK] 服务启动中...
) else (
    echo [!!] 未找到 start.bat，请手动启动服务
    call :write_status "done" "更新完成（需手动启动）"
    del /F /Q "%PACKAGE_PATH%" 2>nul
    goto :eof
)

REM Health check (30s timeout)
echo [^>^>] 等待健康检查...
set "_HEALTH_OK=0"
for /L %%i in (1,1,30) do (
    if !_HEALTH_OK! equ 0 (
        curl -sf http://127.0.0.1:8091/api/health >nul 2>&1
        if !errorlevel! equ 0 (
            set "_HEALTH_OK=1"
        ) else (
            timeout /t 1 /nobreak >nul
        )
    )
)

if !_HEALTH_OK! equ 1 (
    call :write_status "done" "更新完成"
    del /F /Q "%PACKAGE_PATH%" 2>nul
    echo.
    echo [^>^>] =========================================
    echo [OK] 更新完成!
    echo [^>^>] =========================================
) else (
    echo [ERR] 服务未通过健康检查，触发回滚
    goto :rollback
)
goto :eof

:rollback
echo [ERR] 更新失败，正在回滚...
call :write_status "rolling_back" ""
if exist "%BACKUP_DIR%\src" (
    xcopy /E /I /Q /Y "%BACKUP_DIR%\src" "%PROJECT_ROOT%\src" >nul 2>&1
)
if exist "%BACKUP_DIR%\scripts" (
    xcopy /E /I /Q /Y "%BACKUP_DIR%\scripts" "%PROJECT_ROOT%\scripts" >nul 2>&1
)
if exist "%BACKUP_DIR%\client\dist" (
    xcopy /E /I /Q /Y "%BACKUP_DIR%\client\dist" "%PROJECT_ROOT%\client\dist" >nul 2>&1
)
call :write_status "error" "更新失败已回滚"
echo [OK] 已从备份恢复
cd /d "%PROJECT_ROOT%"
if exist "start.bat" (
    start "" cmd /c "start.bat"
)
exit /b 1

:write_status
set "WS_STATUS=%~1"
set "WS_MSG=%~2"
if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data"
if "%WS_MSG%"=="" (
    echo {"status": "%WS_STATUS%", "timestamp": "%date% %time%"} > "%STATUS_FILE%"
) else (
    echo {"status": "%WS_STATUS%", "timestamp": "%date% %time%", "message": "%WS_MSG%"} > "%STATUS_FILE%"
)
goto :eof
