@echo off
chcp 65001 >nul 2>&1
title 闲鱼管家 - 创建桌面快捷方式
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   闲鱼管家 - 桌面快捷方式安装
echo =========================================
echo.

set "PROJECT_ROOT=%~dp0.."
set "DESKTOP=%USERPROFILE%\Desktop"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_NAME=闲鱼管家"

:: Create desktop shortcut
echo [*] 创建桌面快捷方式...
set "VBS=%TEMP%\create_shortcut.vbs"
(
    echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
    echo Set Shortcut = WshShell.CreateShortcut^("%DESKTOP%\%SHORTCUT_NAME%.lnk"^)
    echo Shortcut.TargetPath = "%PROJECT_ROOT%\start.bat"
    echo Shortcut.WorkingDirectory = "%PROJECT_ROOT%"
    echo Shortcut.Description = "闲鱼管家 - 一键启动所有服务"
    echo Shortcut.WindowStyle = 1
    echo Shortcut.Save
) > "%VBS%"
cscript //nologo "%VBS%"
del "%VBS%" >nul 2>&1

if exist "%DESKTOP%\%SHORTCUT_NAME%.lnk" (
    echo [OK] 桌面快捷方式已创建
) else (
    echo [X] 创建桌面快捷方式失败
)

:: Ask about startup
echo.
set /p "ADD_STARTUP=是否添加开机自启动？(y/N): "
if /i "%ADD_STARTUP%"=="y" (
    echo [*] 添加开机自启动...
    set "VBS2=%TEMP%\create_startup.vbs"
    (
        echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
        echo Set Shortcut = WshShell.CreateShortcut^("%STARTUP%\%SHORTCUT_NAME%.lnk"^)
        echo Shortcut.TargetPath = "%PROJECT_ROOT%\start.bat"
        echo Shortcut.WorkingDirectory = "%PROJECT_ROOT%"
        echo Shortcut.Description = "闲鱼管家 - 开机自动启动"
        echo Shortcut.WindowStyle = 7
        echo Shortcut.Save
    ) > "!VBS2!"
    cscript //nologo "!VBS2!"
    del "!VBS2!" >nul 2>&1

    if exist "%STARTUP%\%SHORTCUT_NAME%.lnk" (
        echo [OK] 开机自启动已添加
    ) else (
        echo [X] 添加开机自启动失败
    )
) else (
    echo [OK] 跳过开机自启动
)

echo.
echo =========================================
echo   安装完成
echo =========================================
echo.
echo 提示：
echo   - 双击桌面「%SHORTCUT_NAME%」图标即可启动
echo   - 如需移除自启动，删除以下文件：
echo     %STARTUP%\%SHORTCUT_NAME%.lnk
echo.
pause
