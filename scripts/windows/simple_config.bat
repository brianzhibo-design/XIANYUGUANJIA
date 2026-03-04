@echo off
:: 保存当前代码页并设置UTF-8
for /f "tokens=2 delims=:" %%a in ('chcp') do set "OLD_CP=%%a"
chcp 65001 >nul 2>&1
title 闲鱼自动化 - 简化配置
color 0E
setlocal EnableDelayedExpansion

:: ========================================
:: 简化版配置生成器
:: 只保留必要配置项
:: ========================================

set "PROJECT_DIR=%~dp0..\.."
cd /d "%PROJECT_DIR%"

echo.
echo ===========================================
echo    闲鱼自动化 - 配置向导
echo ===========================================
echo.
echo 本向导将创建最小化配置文件（.env）
echo 只需要配置两个关键项：
echo   1. AI服务API Key（用于智能回复）
echo   2. 闲鱼Cookie（用于登录）
echo.
echo 其他配置使用默认值即可。
echo.
pause

setlocal EnableDelayedExpansion

:: 初始化变量
set "AI_KEY="
set "COOKIE="
set "AI_PROVIDER=deepseek"
set "AI_MODEL=deepseek-chat"
set "AI_BASE_URL=https://api.deepseek.com/v1"

cls
echo.
echo ===========================================
echo    步骤 1/2: 配置AI服务
echo ===========================================
echo.
echo 请选择AI服务提供商:
echo.
echo  [1] DeepSeek (推荐，国内可用)
echo  [2] 阿里云百炼
echo  [3] OpenAI
echo  [4] 自定义OpenAI兼容API
echo.
set /p provider="请选择 (1-4): "

if "!provider!"=="1" (
    set "AI_PROVIDER=deepseek"
    set "AI_MODEL=deepseek-chat"
    set "AI_BASE_URL=https://api.deepseek.com/v1"
    echo.
    echo [*] 已选择: DeepSeek
echo    获取API Key: https://platform.deepseek.com/
)

if "!provider!"=="2" (
    set "AI_PROVIDER=aliyun_bailian"
    set "AI_MODEL=qwen-plus-latest"
    set "AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"
    echo.
    echo [*] 已选择: 阿里云百炼
echo    获取API Key: https://dashscope.console.aliyun.com/
)

if "!provider!"=="3" (
    set "AI_PROVIDER=openai"
    set "AI_MODEL=gpt-4o-mini"
    set "AI_BASE_URL=https://api.openai.com/v1"
    echo.
    echo [*] 已选择: OpenAI
echo    获取API Key: https://platform.openai.com/
)

if "!provider!"=="4" (
    echo.
    echo [*] 自定义OpenAI兼容API
echo.
    set /p AI_BASE_URL="请输入Base URL (如: https://api.example.com/v1): "
    set /p AI_MODEL="请输入模型名称 (如: gpt-3.5-turbo): "
    set "AI_PROVIDER=custom"
)

echo.
set /p AI_KEY="请输入API Key: "

if "!AI_KEY!"=="" (
    echo [!] API Key不能为空
    pause
    exit /b 1
)

cls
echo.
echo ===========================================
echo    步骤 2/2: 配置闲鱼Cookie
echo ===========================================
echo.
echo 获取Cookie方法:
echo  1. 打开浏览器访问 https://www.goofish.com
echo  2. 登录你的闲鱼账号
echo  3. 按F12打开开发者工具 -> 切换到Network标签
echo  4. 刷新页面，点击任意请求
echo  5. 在Request Headers中找到Cookie，复制完整内容
echo.
echo 请选择输入方式:
echo  [1] 直接粘贴Cookie（单行）
echo  [2] 暂时跳过，稍后配置
echo.
set /p cookie_choice="请选择 (1-2): "

set "COOKIE="
if "!cookie_choice!"=="1" (
    echo.
    echo 请粘贴Cookie内容（然后按回车）:
    set /p COOKIE=""
)

if "!COOKIE!"=="" (
    echo [!] Cookie为空，将创建最小配置（稍后可以在Dashboard中添加Cookie）
    set "COOKIE=placeholder_cookie_configure_later"
)

:: 生成配置文件
cls
echo.
echo ===========================================
echo    生成配置文件...
echo ===========================================
echo.

(
echo # =====================================
echo # 闲鱼自动化 - 最小化配置
echo # 生成时间: %date% %time%
echo # =====================================
echo.
echo # ---- AI服务配置 ----
echo AI_PROVIDER=!AI_PROVIDER!
echo AI_API_KEY=!AI_KEY!
echo AI_BASE_URL=!AI_BASE_URL!
echo AI_MODEL=!AI_MODEL!
echo AI_TEMPERATURE=0.7
echo.
echo # ---- 闲鱼账号配置 ----
echo XIANYU_COOKIE_1=!COOKIE!
echo.
echo # ---- 系统配置 ----
echo DATABASE_URL=sqlite:///data/agent.db
echo ENCRYPTION_KEY=auto-generate
echo.
echo # ---- 功能开关 ----
echo QUOTE_ENABLED=true
echo MESSAGES_ENABLED=true
echo WORKFLOW_ENABLED=true
) > .env

echo [✓] 配置文件已保存: .env
echo.
echo 配置摘要:
echo   AI提供商: !AI_PROVIDER!
echo   AI模型: !AI_MODEL!
echo   Cookie长度: !COOKIE:~0,20!...
echo.
echo [!] 如需修改配置，可:
echo    1. 重新运行本向导
echo    2. 直接编辑 .env 文件
echo    3. 使用Dashboard网页界面
echo.
pause
exit /b 0
