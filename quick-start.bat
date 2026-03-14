@echo off
chcp 65001 >nul 2>&1
title 闲鱼管家 - 快速启动引导
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║         闲鱼管家 · 快速启动引导             ║
echo   ║       Xianyu OpenClaw Quick Start           ║
echo   ╚══════════════════════════════════════════════╝
echo.

:: ═══════════════ 0. 网络环境检测 ═══════════════
set "USE_CN_MIRROR=0"
set "PIP_MIRROR_ARGS="
set "NPM_REGISTRY_ARGS="

if "%CHINA_MIRROR%"=="1" (
    set "USE_CN_MIRROR=1"
    goto :mirror_decided
)
if "%CN_MIRROR%"=="1" (
    set "USE_CN_MIRROR=1"
    goto :mirror_decided
)
if "%CHINA_MIRROR%"=="0" goto :mirror_decided
if "%CN_MIRROR%"=="0" goto :mirror_decided

:: 尝试访问 pypi.org 判断网络环境
curl -s --max-time 3 https://pypi.org/ >nul 2>&1
if errorlevel 1 set "USE_CN_MIRROR=1"

:mirror_decided
if "%USE_CN_MIRROR%"=="1" (
    set "PIP_MIRROR_ARGS=-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
    set "NPM_REGISTRY_ARGS=--registry=https://registry.npmmirror.com"
    set "PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright"
    echo   [镜像] 检测到国内网络环境，已自动切换国内镜像源
    echo   --^>  pip  → mirrors.aliyun.com
    echo   --^>  npm  → registry.npmmirror.com
    echo   --^>  Playwright → npmmirror.com
    echo.
    echo   强制使用国际源: set CHINA_MIRROR=0 ^&^& quick-start.bat
) else (
    echo   [镜像] 使用国际源 ^(可设 CHINA_MIRROR=1 强制使用国内源^)
)
echo.

:: ═══════════════ 1. 环境检查 ═══════════════
echo [1/5] 检查运行环境

python --version >nul 2>&1
if errorlevel 1 (
    echo   [NG] 未安装 Python ^(需要 3.10+^)
    echo   --^>  安装: https://python.org
    goto :env_fail
) else (
    for /f "tokens=*" %%v in ('python -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do echo   [OK] Python %%v
)

node --version >nul 2>&1
if errorlevel 1 (
    echo   [NG] 未安装 Node.js ^(需要 18+，前端开发工具^)
    echo   --^>  安装: https://nodejs.org
    goto :env_fail
) else (
    for /f "tokens=*" %%v in ('node -v') do echo   [OK] Node.js %%v（前端开发工具）
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo   [NG] 未安装 npm
    goto :env_fail
) else (
    for /f "tokens=*" %%v in ('npm -v') do echo   [OK] npm %%v
)
echo.
goto :install_deps

:env_fail
echo.
echo   [NG] 缺少必要依赖，请先安装后重新运行
pause
exit /b 1

:: ═══════════════ 2. 依赖安装 ═══════════════
:install_deps
echo [2/5] 安装依赖

if not exist ".venv" (
    echo   --^>  创建 Python 虚拟环境...
    python -m venv .venv
    echo   [OK] 虚拟环境已创建
) else (
    echo   [OK] 虚拟环境已存在
)

call .venv\Scripts\activate.bat

if not exist ".venv\.deps_ok" (
    echo   --^>  安装 Python 依赖 ^(首次约 2 分钟^)...
    pip install -q -r requirements.txt %PIP_MIRROR_ARGS% && echo. > .venv\.deps_ok
    echo   [OK] Python 依赖安装完成
) else (
    echo   [OK] Python 依赖已是最新
)

if not exist "client\node_modules" (
    echo   --^>  安装前端依赖 ^(首次约 1 分钟^)...
    cd client && npm install --silent %NPM_REGISTRY_ARGS% 2>nul && cd ..
    echo   [OK] 前端依赖安装完成
) else (
    echo   [OK] 前端依赖已存在
)

if not exist ".venv\.playwright_ok" (
    echo   --^>  安装 Playwright 浏览器...
    playwright install chromium 2>nul && echo. > .venv\.playwright_ok
    echo   [OK] Playwright 安装完成
) else (
    echo   [OK] Playwright 已就绪
)

:: 确保 data 目录存在
if not exist "data" mkdir data

echo.

:: ═══════════════ 3. 配置检查 ═══════════════
echo [3/5] 检查配置

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo   [!!] .env 已从模板创建，请稍后编辑填入 Cookie
    ) else (
        echo   [!!] 未找到 .env 文件
    )
) else (
    echo   [OK] .env 配置文件存在
)

if exist "config\config.yaml" (
    echo   [OK] config\config.yaml 存在
) else (
    if exist "config\config.example.yaml" (
        copy config\config.example.yaml config\config.yaml >nul
        echo   [!!] config.yaml 已从模板创建
    )
)
echo.

:: ═══════════════ 4. 启动服务 ═══════════════
echo [4/5] 启动服务

echo   --^>  启动 Python 后端 ^(端口 8091^)...
start /b "" python -m src.dashboard_server --port 8091

echo   --^>  启动 React 前端 ^(端口 5173^)...
start /b "" cmd /c "cd client && npx vite --host"

timeout /t 5 /nobreak >nul
echo   [OK] 所有服务已启动
echo.

:: ═══════════════ 5. 完成引导 ═══════════════
echo [5/5] 启动完成
echo.
echo   ┌──────────────────────────────────────────────┐
echo   │  管理面板:     http://localhost:5173         │
echo   │  Python API:   http://localhost:8091         │
echo   │  对话沙盒:     管理面板 → 消息 → 对话沙盒   │
echo   └──────────────────────────────────────────────┘
echo.
echo   首次使用指南:
echo   --^>  1. 打开 http://localhost:5173 进入管理面板
echo   --^>  2. 账户页 → 粘贴闲鱼 Cookie ^(或点击自动获取^)
echo   --^>  3. 系统配置 → 配置 AI ^(推荐百炼千问 Qwen^)
echo   --^>  4. 消息页 → 对话沙盒测试自动回复效果
echo   --^>  5. 确认无误后开启自动回复
echo.
echo   按 Ctrl+C 或关闭窗口停止所有服务
echo.
pause
