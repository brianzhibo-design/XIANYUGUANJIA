#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMMAND_FILE="$SCRIPT_DIR/start.command"
DESKTOP="$HOME/Desktop"

echo ""
echo "========================================="
echo "  闲鱼管家 - macOS 桌面快捷方式安装"
echo "========================================="
echo ""

chmod +x "$COMMAND_FILE"

if [ -d "$DESKTOP" ]; then
    cp "$COMMAND_FILE" "$DESKTOP/闲鱼管家.command"
    chmod +x "$DESKTOP/闲鱼管家.command"
    echo "[OK] 已在桌面创建「闲鱼管家.command」"
    echo "     双击即可启动所有服务"
else
    echo "[!!] 未找到桌面目录: $DESKTOP"
fi

echo ""
read -p "是否添加开机自启动 (LaunchAgent)？(y/N): " ADD_AUTOSTART
if [[ "$ADD_AUTOSTART" =~ ^[Yy]$ ]]; then
    if [ -f "$PROJECT_ROOT/scripts/install-launchd.sh" ]; then
        bash "$PROJECT_ROOT/scripts/install-launchd.sh"
    else
        echo "[!!] 未找到 install-launchd.sh"
    fi
else
    echo "[OK] 跳过开机自启动"
fi

echo ""
echo "========================================="
echo "  安装完成"
echo "========================================="
echo ""
