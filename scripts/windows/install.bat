@echo off
setlocal enabledelayedexpansion

:: ===========================================
:: Xianyu Automation - One-Click Deploy
:: Supports offline deployment (vendor/ directory)
:: ===========================================

:: Get project root directory (parent of scripts/windows/)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_DIR=%CD%"
set "VENDOR_DIR=%PROJECT_DIR%\vendor"

echo [INFO] Project directory: %PROJECT_DIR%

echo.
echo ===========================================
echo    Xianyu Automation - Setup
echo ===========================================
echo.

:: Detect offline mode
set "OFFLINE=0"
if exist "%VENDOR_DIR%\pip-packages" (
    if exist "%VENDOR_DIR%\installers" (
        set "OFFLINE=1"
        echo [MODE] Offline deployment detected (vendor/ found)
    )
)
if "%OFFLINE%"=="0" echo [MODE] Online installation

:: Check if already deployed
if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    echo [OK] Environment already deployed
    goto :CHECK_CONFIG
)

echo [*] Starting first-time setup...
echo.

:: =========================================
:: Step 1: Check/Install Python
:: =========================================
python --version >nul 2>&1
if errorlevel 1 (
    if "%OFFLINE%"=="1" (
        echo [*] Python not found. Installing from offline package...
        for %%f in ("%VENDOR_DIR%\installers\windows\python-*.exe") do (
            echo [*] Running %%~nxf ...
            "%%f" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
            if errorlevel 1 (
                echo [WARN] Silent install failed. Launching installer GUI...
                "%%f"
            )
        )
        :: Refresh PATH
        set "PATH=C:\Program Files\Python312;C:\Program Files\Python312\Scripts;%PATH%"
        python --version >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Python installation failed. Please install manually and restart.
            pause
            exit /b 1
        )
        echo [OK] Python installed from offline package
    ) else (
        echo [*] Python not found. Attempting auto-install via winget...
        winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Python auto-install failed.
            echo Please install Python 3.10+ from https://python.org
            echo Make sure to check "Add Python to PATH"
            pause
            exit /b 1
        )
        echo [OK] Python installed via winget
        echo [INFO] Please restart this script for PATH to take effect.
        pause
        exit /b 0
    )
)

for /f "tokens=*" %%a in ('python --version 2^>^&1') do set "PYTHON_VER=%%a"
echo [OK] Found %PYTHON_VER%

:: =========================================
:: Step 2: Check/Install Node.js
:: =========================================
node --version >nul 2>&1
if errorlevel 1 (
    if "%OFFLINE%"=="1" (
        echo [*] Node.js not found. Installing from offline package...
        for %%f in ("%VENDOR_DIR%\installers\windows\node-*.msi") do (
            echo [*] Running %%~nxf ...
            msiexec /i "%%f" /quiet /norestart
            if errorlevel 1 (
                echo [WARN] Silent install failed. Launching installer GUI...
                msiexec /i "%%f"
            )
        )
        set "PATH=C:\Program Files\nodejs;%PATH%"
        node --version >nul 2>&1
        if errorlevel 1 (
            echo [WARN] Node.js installation may need restart. Frontend will be unavailable.
        ) else (
            echo [OK] Node.js installed from offline package
        )
    ) else (
        echo [*] Node.js not found. Attempting auto-install via winget...
        winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements >nul 2>&1
        if errorlevel 1 (
            echo [WARN] Node.js auto-install failed. Frontend dev server will not be available.
            echo Install from https://nodejs.org if needed.
        ) else (
            echo [OK] Node.js installed via winget
        )
    )
) else (
    for /f "tokens=*" %%a in ('node --version 2^>^&1') do echo [OK] Found Node.js %%a
)

:: =========================================
:: Step 3: Create virtual environment
:: =========================================
echo.
echo [*] Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created

:: =========================================
:: Step 4: Install Python dependencies
:: =========================================
echo.
if "%OFFLINE%"=="1" (
    echo [*] Installing dependencies from offline packages...
    .venv\Scripts\pip install --no-index --find-links "%VENDOR_DIR%\pip-packages\windows-amd64" -r "%PROJECT_DIR%\requirements.txt" -q
) else (
    echo [*] Installing dependencies (this may take a few minutes)...
    .venv\Scripts\pip install -r "%PROJECT_DIR%\requirements.txt" -q
)
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    echo Retrying with updated pip...
    .venv\Scripts\python -m pip install --upgrade pip -q
    if "%OFFLINE%"=="1" (
        .venv\Scripts\pip install --no-index --find-links "%VENDOR_DIR%\pip-packages\windows-amd64" -r "%PROJECT_DIR%\requirements.txt"
    ) else (
        .venv\Scripts\pip install -r "%PROJECT_DIR%\requirements.txt"
    )
    if errorlevel 1 (
        echo [ERROR] Installation failed
        pause
        exit /b 1
    )
)
echo [OK] Dependencies installed

:: =========================================
:: Step 5: Install frontend dependencies
:: =========================================
echo.
node --version >nul 2>&1
if not errorlevel 1 (
    if not exist "%PROJECT_DIR%\client\node_modules" (
        if "%OFFLINE%"=="1" (
            if exist "%VENDOR_DIR%\npm-cache" (
                echo [*] Installing frontend dependencies from offline cache...
                cd /d "%PROJECT_DIR%\client"
                npm install --prefer-offline --cache "%VENDOR_DIR%\npm-cache" --silent 2>nul
                cd /d "%PROJECT_DIR%"
                echo [OK] Frontend dependencies installed (offline)
            )
        ) else (
            echo [*] Installing frontend dependencies...
            cd /d "%PROJECT_DIR%\client"
            npm install --silent 2>nul
            cd /d "%PROJECT_DIR%"
            echo [OK] Frontend dependencies installed
        )
    ) else (
        echo [OK] Frontend dependencies already exist
    )
)

:: Create directories
echo.
echo [*] Creating directories...
mkdir data 2>nul
mkdir logs 2>nul
mkdir config 2>nul
echo [OK] Directories created

:CHECK_CONFIG
:: Check config file
if not exist "%PROJECT_DIR%\.env" (
    if exist "%PROJECT_DIR%\.env.example" (
        copy "%PROJECT_DIR%\.env.example" "%PROJECT_DIR%\.env" >nul
        echo [INFO] .env created from template. Edit it with your configuration.
    ) else (
        echo [INFO] No configuration found
    )
    echo.
    goto :CREATE_CONFIG
)

if not exist "%PROJECT_DIR%\config\config.yaml" (
    if exist "%PROJECT_DIR%\config\config.example.yaml" (
        copy "%PROJECT_DIR%\config\config.example.yaml" "%PROJECT_DIR%\config\config.yaml" >nul
        echo [INFO] config.yaml created from template.
    )
)

echo [OK] Configuration found

echo.
echo ===========================================
echo    Setup Complete!
echo ===========================================
echo.

:: External service guidance
echo --- External Services (Optional) ---
echo.
echo [CookieCloud] Auto cookie sync (recommended):
echo   Server is built-in (no extra setup needed)
echo   Install browser extension:
if exist "%VENDOR_DIR%\extensions\cookiecloud.crx" (
    echo   Offline: Drag vendor\extensions\cookiecloud.crx into Chrome extensions page
) else (
    echo   Chrome: https://chromewebstore.google.com/detail/cookiecloud/ffjiejobkoibkjlhjnlgmcnnigeelbdl
    echo   Edge:   https://microsoftedge.microsoft.com/addons/detail/cookiecloud/bkifenclicgpjhgijmepkiielkeondlg
)
echo   Then configure UUID/password in Dashboard ^> System Config ^> CookieCloud
echo.
echo [BitBrowser] Fingerprint browser (optional, reduces risk detection):
echo   Download from https://www.bitbrowser.net
echo   Configure in Dashboard ^> System Config ^> Slider Verification
echo.

echo Select action:
echo.
echo  [1] Start Main Menu
echo  [2] Reconfigure
echo  [3] Exit
echo.
set /p choice="Select (1-3): "

if "%choice%"=="1" goto :START_MENU
if "%choice%"=="2" goto :CREATE_CONFIG
exit /b 0

:CREATE_CONFIG
call scripts\windows\simple_config.bat
if errorlevel 1 (
    echo [ERROR] Configuration failed
    pause
    exit /b 1
)

:START_MENU
call scripts\windows\menu.bat
exit /b 0
