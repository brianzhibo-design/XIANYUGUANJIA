@echo off
chcp 65001 >nul 2>&1
title 闲鱼管家 - 一键启动
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   闲鱼管家 - 一键启动 (Windows)
echo =========================================
echo.

:: 0. 网络环境检测
set "USE_CN_MIRROR=0"
set "PIP_MIRROR_ARGS="
set "NPM_REGISTRY_ARGS="

if "%CHINA_MIRROR%"=="1" (
    set "USE_CN_MIRROR=1"
    goto :mirror_done
)
if "%CN_MIRROR%"=="1" (
    set "USE_CN_MIRROR=1"
    goto :mirror_done
)
if "%CHINA_MIRROR%"=="0" goto :mirror_done
if "%CN_MIRROR%"=="0" goto :mirror_done

curl -s --max-time 3 https://pypi.org/ >nul 2>&1
if errorlevel 1 set "USE_CN_MIRROR=1"

:mirror_done
if "%USE_CN_MIRROR%"=="1" (
    set "PIP_MIRROR_ARGS=-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
    set "NPM_REGISTRY_ARGS=--registry=https://registry.npmmirror.com"
    echo [OK] 国内网络环境，已切换国内镜像源
)

:: 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [X] 未找到 python，请先安装 Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python 已安装

:: 检查 Node.js（前端开发工具需要）
where node >nul 2>&1
if errorlevel 1 (
    echo [X] 未找到 node，请先安装 Node.js 18+（React 前端开发工具需要）
    pause
    exit /b 1
)
echo [OK] Node.js 已安装（前端开发工具）

:: 创建 .env
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [!] .env 已从 .env.example 创建，请编辑填入实际配置
    ) else (
        echo [X] 未找到 .env 和 .env.example
        pause
        exit /b 1
    )
) else (
    echo [OK] .env 已存在
)

:: 创建 config.yaml
if not exist "config\config.yaml" (
    if exist "config\config.example.yaml" (
        if not exist "config" mkdir config
        copy "config\config.example.yaml" "config\config.yaml" >nul
        echo [OK] config.yaml 已从模板创建
    )
)

:: Python 虚拟环境
if not exist ".venv" (
    echo [*] 创建 Python 虚拟环境...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [OK] Python 虚拟环境已激活

:: 安装依赖
if not exist ".venv\.deps_installed" (
    echo [*] 安装 Python 依赖...
    pip install -q -r requirements.txt %PIP_MIRROR_ARGS%
    echo. > .venv\.deps_installed
)

if not exist "client\node_modules" (
    echo [*] 安装 React 前端依赖...
    cd client && npm install --silent %NPM_REGISTRY_ARGS% && cd ..
)

:: 确保 data 目录存在
if not exist "data" mkdir data

:: 清理被占用端口
for %%p in (8091 5173) do (
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%%p " ^| findstr "LISTENING"') do (
        echo [!] 端口 %%p 被占用 (PID: %%a)，正在释放...
        taskkill /F /PID %%a >nul 2>&1
        timeout /t 1 >nul
    )
)

echo.
echo =========================================
echo   启动所有服务
echo =========================================
echo.

:: 启动 Python 后端
start "Python Backend" cmd /c "call .venv\Scripts\activate.bat && python -m src.dashboard_server --port 8091"

:: 启动 React 前端（Vite dev server）
start "React Frontend" cmd /c "cd client && npx vite --host"

timeout /t 3 >nul

echo.
echo =========================================
echo   所有服务已启动
echo =========================================
echo.
echo [OK] 管理面板:    http://localhost:5173
echo [OK] Python 后端: http://localhost:8091
echo.
echo 关闭此窗口不会停止服务。
echo 如需停止，请关闭对应的命令行窗口。
echo.
pause
