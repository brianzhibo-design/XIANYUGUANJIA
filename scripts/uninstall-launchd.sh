#!/usr/bin/env bash
set -euo pipefail

LABEL="com.openclaw.xianyu"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST_DEST" ]; then
    echo "Unloading $LABEL..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm -f "$PLIST_DEST"
    echo "Removed $PLIST_DEST"
else
    echo "Nothing to uninstall: $PLIST_DEST not found"
fi
