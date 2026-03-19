#!/usr/bin/env bash
set -euo pipefail

NEW_VERSION="${1:?Usage: $0 <version>  例如: $0 9.2.4}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Bumping version to ${NEW_VERSION} ..."

# 1. SSOT: src/__init__.py
sed -i '' "s/__version__ = \".*\"/__version__ = \"${NEW_VERSION}\"/" src/__init__.py
echo "  [OK] src/__init__.py"

# 2. client/package.json
(cd client && npm version "$NEW_VERSION" --no-git-tag-version --allow-same-version >/dev/null 2>&1)
echo "  [OK] client/package.json"

# 3. config/config.example.yaml
sed -i '' "s/^  version: \".*\"/  version: \"${NEW_VERSION}\"/" config/config.example.yaml
echo "  [OK] config/config.example.yaml"

# 4. README.md title
sed -i '' "s/闲鱼管家) v[0-9][0-9.]*/闲鱼管家) v${NEW_VERSION}/" README.md
echo "  [OK] README.md"

# 5. config/config.yaml (local user config, if exists)
if [ -f config/config.yaml ]; then
    sed -i '' "s/^  version: .*/  version: \"${NEW_VERSION}\"/" config/config.yaml
    echo "  [OK] config/config.yaml"
fi

echo ""
echo "Version bumped to ${NEW_VERSION}"
echo ""
echo "以下文件运行时自动读取 src/__init__.py，无需手动修改："
echo "  - src/core/config_models.py (import __version__)"
echo "  - src/core/config.py        (__import__('src').__version__)"
echo "  - src/dashboard/routes/system.py"
echo "  - scripts/macos/start.command"
