#!/usr/bin/env bash
# 闲鱼管家 - 离线安装包构建脚本
#
# 产出:
#   dist/xianyu-openclaw-vX.Y.Z-full.tar.gz       通用包 (macOS + Windows)
#   dist/xianyu-openclaw-vX.Y.Z-macos-arm64.tar.gz macOS 专用包
#   dist/xianyu-openclaw-vX.Y.Z-windows-x64.zip    Windows 专用包
#
# 用法:
#   bash scripts/build_release.sh
#   bash scripts/build_release.sh --skip-vendor   # 跳过离线依赖下载（vendor/ 已存在时）
#   bash scripts/build_release.sh --skip-frontend  # 跳过前端构建（client/dist/ 已存在时）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[1;34m'; C='\033[0;36m'; W='\033[1;37m'; N='\033[0m'
ok()   { printf "${G}  [OK]${N} %s\n" "$1"; }
warn() { printf "${Y}  [!!]${N} %s\n" "$1"; }
fail() { printf "${R}[ERR]${N} %s\n" "$1"; exit 1; }
step() { printf "\n${B}==> %s${N}\n" "$1"; }

SKIP_VENDOR=0
SKIP_FRONTEND=0
for arg in "$@"; do
  case "$arg" in
    --skip-vendor)   SKIP_VENDOR=1 ;;
    --skip-frontend) SKIP_FRONTEND=1 ;;
  esac
done

# ═══════════════ 读取版本号 ═══════════════
VERSION=$(python3 -c 'import re,pathlib; m=re.search(r"__version__\s*=\s*[\"'"'"'](.*?)[\"'"'"']", pathlib.Path("src/__init__.py").read_text()); print(m.group(1) if m else "0.0.0")' 2>/dev/null || grep -oP '__version__\s*=\s*"\K[^"]+' src/__init__.py 2>/dev/null || echo "0.0.0")

RELEASE_NAME="xianyu-openclaw-v${VERSION}"
DIST_DIR="$PROJECT_ROOT/dist"
STAGING_DIR="$DIST_DIR/.staging/${RELEASE_NAME}"

printf "${W}"
cat << BANNER

  ╔══════════════════════════════════════════════╗
  ║      闲鱼管家 · 安装包构建工具              ║
  ║      v${VERSION}                                  ║
  ╚══════════════════════════════════════════════╝

BANNER
printf "${N}"

echo "  版本:   v${VERSION}"
echo "  产出:   dist/${RELEASE_NAME}-*.tar.gz / .zip"
echo ""

# ═══════════════ 1. 构建前端 ═══════════════
step "[1/5] 构建前端"

if [ "$SKIP_FRONTEND" -eq 1 ] && [ -d "client/dist" ]; then
  ok "前端构建跳过 (--skip-frontend, client/dist/ 已存在)"
else
  if ! command -v npm &>/dev/null; then
    fail "需要 npm 来构建前端"
  fi

  (cd client && npm install --silent 2>/dev/null && npm run build 2>&1 | tail -5)

  if [ -d "client/dist" ]; then
    FRONTEND_SIZE=$(du -sh client/dist | cut -f1)
    ok "前端构建完成 (${FRONTEND_SIZE})"
  else
    fail "前端构建失败: client/dist/ 不存在"
  fi
fi

# ═══════════════ 2. 准备离线依赖 ═══════════════
step "[2/5] 准备离线依赖"

if [ "$SKIP_VENDOR" -eq 1 ] && [ -d "vendor" ] && [ -f "vendor/manifest.json" ]; then
  VENDOR_SIZE=$(du -sh vendor | cut -f1)
  ok "离线依赖跳过 (--skip-vendor, vendor/ 已存在, ${VENDOR_SIZE})"
else
  if [ -f "scripts/prepare_offline.sh" ]; then
    bash scripts/prepare_offline.sh --platform all
    ok "离线依赖准备完成"
  else
    fail "scripts/prepare_offline.sh 不存在"
  fi
fi

# ═══════════════ 3. 创建临时打包目录 ═══════════════
step "[3/5] 组装打包内容"

rm -rf "$DIST_DIR/.staging"
mkdir -p "$STAGING_DIR"

INCLUDE_DIRS=(
  src
  config
  vendor
  scripts
)

INCLUDE_CLIENT=(
  client/dist
  client/src
  client/package.json
  client/package-lock.json
  client/nginx.conf
  client/vite.config.js
  client/tsconfig.json
  client/tsconfig.node.json
  client/tailwind.config.js
  client/postcss.config.js
  client/index.html
)

INCLUDE_ROOT_FILES=(
  requirements.txt
  requirements-windows.txt
  .env.example
  start.sh
  start.bat
  quick-start.sh
  quick-start.bat
  pyproject.toml
  package.json
  pyinstaller.spec
  QUICKSTART.md
  README.md
  LICENSE
)

for dir in "${INCLUDE_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    cp -a "$dir" "$STAGING_DIR/$dir"
  fi
done

mkdir -p "$STAGING_DIR/client"
for item in "${INCLUDE_CLIENT[@]}"; do
  if [ -e "$item" ]; then
    cp -a "$item" "$STAGING_DIR/$item"
  fi
done

for f in "${INCLUDE_ROOT_FILES[@]}"; do
  if [ -e "$f" ]; then
    cp -a "$f" "$STAGING_DIR/$f"
  fi
done

mkdir -p "$STAGING_DIR/data" "$STAGING_DIR/logs"

# 排除不需要的文件
find "$STAGING_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGING_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$STAGING_DIR" -name ".DS_Store" -delete 2>/dev/null || true
find "$STAGING_DIR" -name "*.bak.*" -delete 2>/dev/null || true
find "$STAGING_DIR" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
rm -f "$STAGING_DIR/config/config.yaml" 2>/dev/null || true

FILE_COUNT=$(find "$STAGING_DIR" -type f | wc -l | tr -d ' ')
STAGING_SIZE=$(du -sh "$STAGING_DIR" | cut -f1)
ok "打包目录就绪: ${FILE_COUNT} 文件, ${STAGING_SIZE}"

# ═══════════════ 4. 创建安装包 ═══════════════
step "[4/5] 创建安装包"

mkdir -p "$DIST_DIR"

# --- 4a. 通用包 (full) ---
FULL_TAR="$DIST_DIR/${RELEASE_NAME}-full.tar.gz"
printf "  创建通用包..."
(cd "$DIST_DIR/.staging" && tar czf "$FULL_TAR" "$RELEASE_NAME")
FULL_SIZE=$(du -sh "$FULL_TAR" | cut -f1)
printf "\r"
ok "通用包: ${RELEASE_NAME}-full.tar.gz (${FULL_SIZE})"

# --- 4b. macOS 专用包 ---
MACOS_STAGING="$DIST_DIR/.staging-macos/${RELEASE_NAME}"
rm -rf "$DIST_DIR/.staging-macos"
mkdir -p "$DIST_DIR/.staging-macos"
cp -a "$STAGING_DIR" "$MACOS_STAGING"

# 移除 Windows 专属内容
rm -rf "$MACOS_STAGING/vendor/installers/windows" 2>/dev/null || true
rm -rf "$MACOS_STAGING/vendor/pip-packages/windows-amd64" 2>/dev/null || true
rm -f "$MACOS_STAGING/start.bat" "$MACOS_STAGING/quick-start.bat" 2>/dev/null || true
rm -rf "$MACOS_STAGING/scripts/windows" 2>/dev/null || true
rm -f "$MACOS_STAGING/scripts/install-desktop.bat" 2>/dev/null || true
rm -f "$MACOS_STAGING/requirements-windows.txt" 2>/dev/null || true
rm -f "$MACOS_STAGING/pyinstaller.spec" 2>/dev/null || true

MACOS_TAR="$DIST_DIR/${RELEASE_NAME}-macos-arm64.tar.gz"
printf "  创建 macOS 包..."
(cd "$DIST_DIR/.staging-macos" && tar czf "$MACOS_TAR" "$RELEASE_NAME")
MACOS_SIZE=$(du -sh "$MACOS_TAR" | cut -f1)
printf "\r"
ok "macOS 包: ${RELEASE_NAME}-macos-arm64.tar.gz (${MACOS_SIZE})"
rm -rf "$DIST_DIR/.staging-macos"

# --- 4c. Windows 专用包 ---
WIN_STAGING="$DIST_DIR/.staging-windows/${RELEASE_NAME}"
rm -rf "$DIST_DIR/.staging-windows"
mkdir -p "$DIST_DIR/.staging-windows"
cp -a "$STAGING_DIR" "$WIN_STAGING"

# 移除 macOS 专属内容
rm -rf "$WIN_STAGING/vendor/installers/macos" 2>/dev/null || true
rm -rf "$WIN_STAGING/vendor/pip-packages/macos-arm64" 2>/dev/null || true
rm -f "$WIN_STAGING/start.sh" "$WIN_STAGING/quick-start.sh" 2>/dev/null || true
rm -rf "$WIN_STAGING/scripts/macos" 2>/dev/null || true
rm -rf "$WIN_STAGING/scripts/unix" 2>/dev/null || true
rm -f "$WIN_STAGING/scripts/install-launchd.sh" "$WIN_STAGING/scripts/uninstall-launchd.sh" 2>/dev/null || true

WIN_ZIP="$DIST_DIR/${RELEASE_NAME}-windows-x64.zip"
printf "  创建 Windows 包..."
if command -v zip &>/dev/null; then
  (cd "$DIST_DIR/.staging-windows" && zip -r -q "$WIN_ZIP" "$RELEASE_NAME")
else
  # 无 zip 命令时用 tar.gz 代替
  WIN_ZIP="$DIST_DIR/${RELEASE_NAME}-windows-x64.tar.gz"
  (cd "$DIST_DIR/.staging-windows" && tar czf "$WIN_ZIP" "$RELEASE_NAME")
fi
WIN_SIZE=$(du -sh "$WIN_ZIP" | cut -f1)
printf "\r"
ok "Windows 包: $(basename "$WIN_ZIP") (${WIN_SIZE})"
rm -rf "$DIST_DIR/.staging-windows"

# --- 4d. 源码更新包 (update, ~7MB, 不含 vendor/config/data) ---
UPDATE_STAGING="$DIST_DIR/.staging-update/${RELEASE_NAME}"
rm -rf "$DIST_DIR/.staging-update"
mkdir -p "$UPDATE_STAGING"

UPDATE_DIRS=(src scripts)
UPDATE_CLIENT_ITEMS=(client/dist client/src client/package.json client/package-lock.json
  client/vite.config.js client/tsconfig.json client/tsconfig.node.json
  client/tailwind.config.js client/postcss.config.js client/index.html)
UPDATE_ROOT_FILES=(requirements.txt start.sh start.bat quick-start.sh quick-start.bat)

for dir in "${UPDATE_DIRS[@]}"; do
  [ -d "$STAGING_DIR/$dir" ] && cp -a "$STAGING_DIR/$dir" "$UPDATE_STAGING/$dir"
done
mkdir -p "$UPDATE_STAGING/client"
for item in "${UPDATE_CLIENT_ITEMS[@]}"; do
  [ -e "$STAGING_DIR/$item" ] && cp -a "$STAGING_DIR/$item" "$UPDATE_STAGING/$item"
done
for f in "${UPDATE_ROOT_FILES[@]}"; do
  [ -e "$STAGING_DIR/$f" ] && cp -a "$STAGING_DIR/$f" "$UPDATE_STAGING/$f"
done

UPDATE_TAR="$DIST_DIR/${RELEASE_NAME}-update.tar.gz"
printf "  创建更新包..."
(cd "$DIST_DIR/.staging-update" && tar czf "$UPDATE_TAR" "$RELEASE_NAME")
UPDATE_SIZE=$(du -sh "$UPDATE_TAR" | cut -f1)
printf "\r"
ok "更新包: ${RELEASE_NAME}-update.tar.gz (${UPDATE_SIZE})"
rm -rf "$DIST_DIR/.staging-update"

# 清理临时目录
rm -rf "$DIST_DIR/.staging"

# ═══════════════ 5. 生成校验和 ═══════════════
step "[5/5] 生成校验和"

CHECKSUMS="$DIST_DIR/${RELEASE_NAME}-checksums.txt"
: > "$CHECKSUMS"
for f in "$DIST_DIR/${RELEASE_NAME}-"*; do
  [ "$f" = "$CHECKSUMS" ] && continue
  [ -f "$f" ] || continue
  sha=$(shasum -a 256 "$f" | cut -d' ' -f1)
  size=$(du -sh "$f" | cut -f1)
  basename_f=$(basename "$f")
  printf "%s  %s  (%s)\n" "$sha" "$basename_f" "$size" >> "$CHECKSUMS"
  echo "  $sha  $basename_f  ($size)"
done
ok "校验和: ${RELEASE_NAME}-checksums.txt"

# ═══════════════ 完成 ═══════════════
echo ""
printf "${W}"
cat << DONE
  ╔══════════════════════════════════════════════╗
  ║           构建完成                           ║
  ╠══════════════════════════════════════════════╣
  ║  版本: v${VERSION}                                 ║
  ║  位置: dist/                                 ║
  ╚══════════════════════════════════════════════╝
DONE
printf "${N}"
echo ""
echo "  产出文件:"
ls -lh "$DIST_DIR/${RELEASE_NAME}-"* 2>/dev/null | awk '{printf "    %-50s %s\n", $NF, $5}'
echo ""
printf "${Y}  部署方式:${N}\n"
echo "  macOS:   tar xzf ${RELEASE_NAME}-macos-arm64.tar.gz && cd ${RELEASE_NAME} && bash quick-start.sh"
echo "  Windows: 解压 ${RELEASE_NAME}-windows-x64.zip → 双击 quick-start.bat"
echo "  通用:    tar xzf ${RELEASE_NAME}-full.tar.gz（包含双平台依赖）"
echo ""
