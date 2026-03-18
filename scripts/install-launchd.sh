#!/usr/bin/env bash
set -euo pipefail

LABEL="com.xianyu-guanjia"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_TEMPLATE="$SCRIPT_DIR/macos/${LABEL}.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

# 优先使用 venv 中的 Python3
PYTHON3=""
if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON3="$PROJECT_ROOT/.venv/bin/python3"
elif [ -x "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON3="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON3="$(command -v python3 2>/dev/null || true)"
fi

if [ -z "$PYTHON3" ]; then
    echo "Error: python3 not found in PATH or .venv"
    exit 1
fi

# 卸载旧的 Label（兼容旧版 com.openclaw.xianyu、com.xianyu-openclaw）
for old_label in "com.openclaw.xianyu" "com.xianyu-openclaw" "$LABEL"; do
    old_plist="$HOME/Library/LaunchAgents/${old_label}.plist"
    if launchctl list "$old_label" &>/dev/null; then
        echo "Unloading existing $old_label..."
        launchctl unload "$old_plist" 2>/dev/null || true
    fi
    [ -f "$old_plist" ] && [ "$old_plist" != "$PLIST_DEST" ] && rm -f "$old_plist"
done

mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$HOME/Library/LaunchAgents"

sed \
    -e "s|__PYTHON3__|$PYTHON3|g" \
    -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

launchctl load "$PLIST_DEST"

echo ""
echo "✅ Installed and loaded $LABEL"
echo "  Python:  $PYTHON3"
echo "  Project: $PROJECT_ROOT"
echo "  Plist:   $PLIST_DEST"
echo ""
echo "Commands:"
echo "  launchctl start $LABEL    # start now"
echo "  launchctl stop  $LABEL    # stop (will restart on crash)"
echo "  bash scripts/macos/install_service.sh uninstall  # remove completely"
