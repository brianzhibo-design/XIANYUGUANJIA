#!/usr/bin/env bash
set -euo pipefail

LABEL="com.openclaw.xianyu"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_TEMPLATE="$SCRIPT_DIR/$LABEL.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

PYTHON3="$(command -v python3 2>/dev/null || true)"
if [ -z "$PYTHON3" ]; then
    echo "Error: python3 not found in PATH"
    exit 1
fi

if launchctl list "$LABEL" &>/dev/null; then
    echo "Unloading existing $LABEL..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$HOME/Library/LaunchAgents"

sed \
    -e "s|__PYTHON3__|$PYTHON3|g" \
    -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

launchctl load "$PLIST_DEST"

echo "Installed and loaded $LABEL"
echo "  Python:  $PYTHON3"
echo "  Project: $PROJECT_ROOT"
echo "  Plist:   $PLIST_DEST"
echo ""
echo "Commands:"
echo "  launchctl start $LABEL    # start now"
echo "  launchctl stop  $LABEL    # stop (will restart on crash)"
echo "  bash scripts/uninstall-launchd.sh  # remove completely"
