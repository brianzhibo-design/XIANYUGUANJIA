@echo off
setlocal enabledelayedexpansion

:: ===========================================
:: Xianyu Automation - Offline Package Prep
:: Run on a machine WITH internet access
:: ===========================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_DIR=%CD%"
set "VENDOR_DIR=%PROJECT_DIR%\vendor"

set "PYTHON_VER=3.12.8"
set "NODE_VER=v20.18.1"
set "TARGET_PYVER=3.12"

echo.
echo ===========================================
echo    Offline Package Preparation Tool
echo ===========================================
echo.
echo [INFO] Project: %PROJECT_DIR%
echo [INFO] Output:  %VENDOR_DIR%
echo.

:: Check tools
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python first.
    pause
    exit /b 1
)
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found.
    pause
    exit /b 1
)
curl --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl not found.
    pause
    exit /b 1
)
echo [OK] Tools ready

:: Create directory structure
echo.
echo [1/4] Creating directory structure...
mkdir "%VENDOR_DIR%\installers\macos" 2>nul
mkdir "%VENDOR_DIR%\installers\windows" 2>nul
mkdir "%VENDOR_DIR%\pip-packages\macos-arm64" 2>nul
mkdir "%VENDOR_DIR%\pip-packages\windows-amd64" 2>nul
mkdir "%VENDOR_DIR%\npm-cache" 2>nul
mkdir "%VENDOR_DIR%\extensions" 2>nul
echo [OK] Directory structure created

:: Download Python installer (Windows)
echo.
echo [2/4] Downloading installers...

if not exist "%VENDOR_DIR%\installers\windows\python-%PYTHON_VER%-amd64.exe" (
    echo [*] Downloading Python %PYTHON_VER% Windows installer...
    curl -L --progress-bar -o "%VENDOR_DIR%\installers\windows\python-%PYTHON_VER%-amd64.exe" ^
        "https://www.python.org/ftp/python/%PYTHON_VER%/python-%PYTHON_VER%-amd64.exe"
    echo [OK] Python installer downloaded
) else (
    echo [OK] Python installer already exists
)

:: Download Node.js installer (Windows)
if not exist "%VENDOR_DIR%\installers\windows\node-%NODE_VER%-x64.msi" (
    echo [*] Downloading Node.js %NODE_VER% Windows installer...
    curl -L --progress-bar -o "%VENDOR_DIR%\installers\windows\node-%NODE_VER%-x64.msi" ^
        "https://npmmirror.com/mirrors/node/%NODE_VER%/node-%NODE_VER%-x64.msi"
    echo [OK] Node.js installer downloaded
) else (
    echo [OK] Node.js installer already exists
)

:: Download macOS installers too (cross-platform via curl)
if not exist "%VENDOR_DIR%\installers\macos\python-%PYTHON_VER%-macos11.pkg" (
    echo [*] Downloading Python %PYTHON_VER% macOS installer...
    curl -L --progress-bar -o "%VENDOR_DIR%\installers\macos\python-%PYTHON_VER%-macos11.pkg" ^
        "https://www.python.org/ftp/python/%PYTHON_VER%/python-%PYTHON_VER%-macos11.pkg"
    echo [OK] Python macOS installer downloaded
) else (
    echo [OK] Python macOS installer already exists
)

if not exist "%VENDOR_DIR%\installers\macos\node-%NODE_VER%.pkg" (
    echo [*] Downloading Node.js %NODE_VER% macOS installer...
    curl -L --progress-bar -o "%VENDOR_DIR%\installers\macos\node-%NODE_VER%.pkg" ^
        "https://npmmirror.com/mirrors/node/%NODE_VER%/node-%NODE_VER%.pkg"
    echo [OK] Node.js macOS installer downloaded
) else (
    echo [OK] Node.js macOS installer already exists
)

:: Download pip packages
echo.
echo [3/4] Downloading Python packages...

echo [*] Windows x64 wheels...
pip download -r "%PROJECT_DIR%\requirements.txt" ^
    --platform win_amd64 --python-version %TARGET_PYVER% ^
    --only-binary=:all: ^
    -d "%VENDOR_DIR%\pip-packages\windows-amd64\" 2>nul
:: Supplement sdist-only packages (e.g. oss2)
pip download -r "%PROJECT_DIR%\requirements.txt" ^
    --no-binary=:all: --no-deps ^
    -d "%VENDOR_DIR%\pip-packages\windows-amd64\" 2>nul
echo [OK] Windows pip packages downloaded

echo [*] macOS ARM64 wheels...
pip download -r "%PROJECT_DIR%\requirements.txt" ^
    --platform macosx_11_0_arm64 --python-version %TARGET_PYVER% ^
    --only-binary=:all: ^
    -d "%VENDOR_DIR%\pip-packages\macos-arm64\" 2>nul
pip download -r "%PROJECT_DIR%\requirements.txt" ^
    --no-binary=:all: --no-deps ^
    -d "%VENDOR_DIR%\pip-packages\macos-arm64\" 2>nul
echo [OK] macOS pip packages downloaded

:: npm cache
echo.
echo [4/4] Caching frontend dependencies...
node --version >nul 2>&1
if not errorlevel 1 (
    cd /d "%PROJECT_DIR%\client"
    npm install --cache "%VENDOR_DIR%\npm-cache" --prefer-offline --silent 2>nul
    cd /d "%PROJECT_DIR%"
    echo [OK] npm cache populated
) else (
    echo [WARN] Node.js not available, skipping npm cache
)

:: CookieCloud extension guidance
echo.
echo [INFO] CookieCloud browser extension - manual download:
echo   Chrome: https://chromewebstore.google.com/detail/cookiecloud/ffjiejobkoibkjlhjnlgmcnnigeelbdl
echo   Edge:   https://microsoftedge.microsoft.com/addons/detail/cookiecloud/bkifenclicgpjhgijmepkiielkeondlg
echo   Save .crx to: vendor\extensions\cookiecloud.crx

echo.
echo ===========================================
echo    Offline Package Preparation Complete
echo ===========================================
echo.
echo Next steps:
echo   1. Copy entire project folder to USB drive
echo   2. On new device, copy from USB to local disk
echo   3. Run scripts\windows\install.bat
echo   4. Script will detect vendor\ and install offline
echo.
pause
exit /b 0
