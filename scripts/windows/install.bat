@echo off
:: 保存当前代码页并设置UTF-8
for /f "tokens=2 delims=:" %%a in ('chcp') do set "OLD_CP=%%a"
chcp 65001 >nul 2>&1
title 闲鱼自动化 - 一键部署
color 0B

:: ========================================
:: 闲鱼自动化 - Windows一键部署脚本
:: 完全脱离Docker和OpenClaw Gateway
:: ========================================

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ===========================================
echo    闲鱼自动化 - Windows一键部署
echo ===========================================
echo.

:: 检查是否已部署
if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    echo [✓] 检测到已部署环境
    goto :CHECK_CONFIG
)

echo [*] 开始首次部署...
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] 未检测到Python，请先安装Python 3.10+
    echo     下载地址: https://www.python.org/downloads/
    echo     安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=*" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo [✓] 检测到 %PYTHON_VERSION%

:: 创建虚拟环境
echo.
echo [*] 创建Python虚拟环境...
python -m venv .venv
if errorlevel 1 (
    echo [!] 创建虚拟环境失败
    pause
    exit /b 1
)
echo [✓] 虚拟环境创建成功

:: 安装依赖
echo.
echo [*] 安装依赖包（可能需要几分钟）...
.venv\Scripts\pip install -r requirements.txt -q
if errorlevel 1 (
    echo [!] 依赖安装失败，尝试升级pip后重试...
    .venv\Scripts\python -m pip install --upgrade pip -q
    .venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo [!] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)
echo [✓] 依赖安装完成

:: 创建必要目录
echo.
echo [*] 创建数据目录...
mkdir data 2>nul
mkdir logs 2>nul
mkdir config 2>nul
echo [✓] 目录创建完成

:CHECK_CONFIG
:: 检查配置文件
if not exist "%PROJECT_DIR%\.env" (
    echo.
    echo [!] 未检测到配置文件，需要创建
    echo.
    goto :CREATE_CONFIG
)

echo [✓] 检测到配置文件

echo.
echo ===========================================
echo    部署完成！
echo ===========================================
echo.
echo 请选择操作:
echo.
echo  [1] 启动主菜单
echo  [2] 重新配置
echo  [3] 退出
echo.
set /p choice="请输入选项 (1-3): "

if "%choice%"=="1" goto :START_MENU
if "%choice%"=="2" goto :CREATE_CONFIG
exit /b 0

:CREATE_CONFIG
call scripts\windows\simple_config.bat
if errorlevel 1 (
    echo [!] 配置创建失败
    pause
    exit /b 1
)

:START_MENU
call scripts\windows\menu.bat
exit /b 0
