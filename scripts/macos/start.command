#!/usr/bin/env bash
# 闲鱼管家 - macOS 双击启动
# 将此文件拖到桌面或 Dock，双击即可启动所有服务

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo ""
echo "========================================="
echo "  闲鱼管家 - macOS 启动"
echo "========================================="
echo ""

if [ -f "start.sh" ]; then
    exec bash start.sh
else
    echo "正在启动后端服务..."
    python3 -m src.dashboard_server --port 8091 &
    BACKEND_PID=$!

    if [ -d "client" ] && [ -f "client/package.json" ]; then
        echo "正在启动前端..."
        cd client && npx vite --host &
        FRONTEND_PID=$!
        cd "$PROJECT_ROOT"
    fi

    echo ""
    echo "服务已启动:"
    echo "  管理面板: http://localhost:5173"
    echo "  后端 API: http://localhost:8091"
    echo ""
    echo "关闭此终端窗口将停止所有服务。"
    echo "按 Ctrl+C 停止..."

    trap "kill $BACKEND_PID ${FRONTEND_PID:-} 2>/dev/null; exit 0" INT TERM
    wait
fi
