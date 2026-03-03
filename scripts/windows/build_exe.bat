@echo off
chcp 65001 >nul 2>&1
setlocal

echo ============================================
echo   闲鱼 OpenClaw - Windows EXE 构建脚本
echo ============================================
echo.

:: Navigate to project root
cd /d "%~dp0\..\.."

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: Create/activate venv if not exists
if not exist ".venv" (
    echo [1/4] 创建虚拟环境...
    python -m venv .venv
)

echo [1/4] 激活虚拟环境...
call .venv\Scripts\activate.bat

echo [2/4] 安装依赖...
pip install -r requirements.txt -r requirements-windows.txt --quiet

echo [3/4] 开始构建 EXE（onedir 模式）...
echo       这可能需要几分钟，请耐心等待...
echo.
pyinstaller pyinstaller.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 构建失败！请检查上方错误信息。
    pause
    exit /b 1
)

echo.
echo [4/4] 构建完成！
echo.
echo   输出目录: dist\xianyu-openclaw-launcher\
echo   启动程序: dist\xianyu-openclaw-launcher\xianyu-openclaw-launcher.exe
echo.
echo   发布时，将整个 dist\xianyu-openclaw-launcher\ 文件夹打包为 ZIP 即可。
echo.
pause
