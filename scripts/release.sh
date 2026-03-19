#!/usr/bin/env bash
# 闲鱼管家 - 一键发版脚本
#
# 用法:
#   bash scripts/release.sh <version>
#   bash scripts/release.sh 9.2.6
#
# 流程: bump版本 -> 构建前端 -> 打包update.tar.gz -> git commit+push -> 创建Release -> 上传asset
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[1;34m'; W='\033[1;37m'; N='\033[0m'
ok()   { printf "${G}  [OK]${N} %s\n" "$1"; }
warn() { printf "${Y}  [!!]${N} %s\n" "$1"; }
fail() { printf "${R}[ERR]${N} %s\n" "$1"; exit 1; }
step() { printf "\n${B}==> %s${N}\n" "$1"; }

NEW_VERSION="${1:?用法: bash scripts/release.sh <version>  例如: bash scripts/release.sh 9.2.6}"
TAG="v${NEW_VERSION}"
RELEASE_NAME="xianyu-openclaw-${TAG}"
DIST_DIR="$PROJECT_ROOT/dist"
REPO="brianzhibo-design/XIANYUGUANJIA"

printf "${W}"
cat << BANNER

  ╔══════════════════════════════════════════════╗
  ║      闲鱼管家 · 一键发版                    ║
  ║      ${TAG}                                    ║
  ╚══════════════════════════════════════════════╝

BANNER
printf "${N}"

# ═══════════════ 前置检查 ═══════════════
step "[0/6] 前置检查"

command -v gh  >/dev/null 2>&1 || fail "需要 gh CLI (brew install gh)"
command -v npm >/dev/null 2>&1 || fail "需要 npm"
command -v git >/dev/null 2>&1 || fail "需要 git"

if ! git diff --quiet 2>/dev/null; then
  warn "工作区有未提交的修改，将在 bump 后一并提交"
fi

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  warn "Release $TAG 已存在，将仅上传 asset（跳过创建）"
  RELEASE_EXISTS=1
else
  RELEASE_EXISTS=0
fi

ok "前置检查通过"

# ═══════════════ 1. Bump 版本号 ═══════════════
step "[1/6] Bump 版本号 -> ${NEW_VERSION}"

if [ -f "$SCRIPT_DIR/bump_version.sh" ]; then
  bash "$SCRIPT_DIR/bump_version.sh" "$NEW_VERSION"
else
  fail "scripts/bump_version.sh 不存在"
fi

# ═══════════════ 2. 构建前端 ═══════════════
step "[2/6] 构建前端"

(cd client && npm run build 2>&1 | tail -5)

if [ -d "client/dist" ]; then
  FRONTEND_SIZE=$(du -sh client/dist | cut -f1)
  ok "前端构建完成 (${FRONTEND_SIZE})"
else
  fail "前端构建失败: client/dist/ 不存在"
fi

# ═══════════════ 3. 打包更新包 ═══════════════
step "[3/6] 打包更新包"

STAGING="$DIST_DIR/.staging-update/${RELEASE_NAME}"
rm -rf "$DIST_DIR/.staging-update"
mkdir -p "$STAGING/client"

UPDATE_DIRS=(src scripts)
UPDATE_CLIENT_ITEMS=(
  client/dist client/src client/package.json client/package-lock.json
  client/vite.config.js client/tsconfig.json client/tsconfig.node.json
  client/tailwind.config.js client/postcss.config.js client/index.html
)
UPDATE_ROOT_FILES=(requirements.txt start.sh start.bat quick-start.sh quick-start.bat README.md)

for dir in "${UPDATE_DIRS[@]}"; do
  [ -d "$dir" ] && cp -a "$dir" "$STAGING/$dir"
done
for item in "${UPDATE_CLIENT_ITEMS[@]}"; do
  [ -e "$item" ] && cp -a "$item" "$STAGING/$item"
done
for f in "${UPDATE_ROOT_FILES[@]}"; do
  [ -e "$f" ] && cp -a "$f" "$STAGING/$f"
done

find "$STAGING" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGING" -name "*.pyc" -delete 2>/dev/null || true
find "$STAGING" -name ".DS_Store" -delete 2>/dev/null || true
find "$STAGING" -name "*.bak.*" -delete 2>/dev/null || true
find "$STAGING" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
rm -f "$STAGING/config/config.yaml" 2>/dev/null || true

UPDATE_TAR="$DIST_DIR/${RELEASE_NAME}-update.tar.gz"
(cd "$DIST_DIR/.staging-update" && tar czf "$UPDATE_TAR" "$RELEASE_NAME")
UPDATE_SIZE=$(du -sh "$UPDATE_TAR" | cut -f1)
ok "更新包: ${RELEASE_NAME}-update.tar.gz (${UPDATE_SIZE})"

rm -rf "$DIST_DIR/.staging-update"

# ═══════════════ 4. 生成 SHA256 校验和 ═══════════════
step "[4/6] 生成 SHA256 校验和"

CHECKSUM_FILE="$DIST_DIR/${RELEASE_NAME}-checksums.txt"
(cd "$DIST_DIR" && shasum -a 256 "$(basename "$UPDATE_TAR")") > "$CHECKSUM_FILE"
ok "校验和: $(cat "$CHECKSUM_FILE")"

# ═══════════════ 5. Git commit + push ═══════════════
step "[5/6] Git commit + push"

git add -A
if git diff --cached --quiet 2>/dev/null; then
  ok "无新增修改，跳过提交"
else
  git commit -m "release: ${TAG}" --quiet
  ok "已提交: release: ${TAG}"
fi

git push origin main --quiet
ok "已推送至 origin/main"

# ═══════════════ 6. 创建 Release + 上传 asset ═══════════════
step "[6/6] 创建 Release + 上传 asset"

if [ "$RELEASE_EXISTS" -eq 0 ]; then
  gh release create "$TAG" \
    --repo "$REPO" \
    --title "${TAG}" \
    --generate-notes
  ok "Release $TAG 已创建"
fi

gh release upload "$TAG" \
  "$UPDATE_TAR" \
  "$CHECKSUM_FILE" \
  --repo "$REPO" \
  --clobber
ok "Asset 已上传"

# ═══════════════ 完成 ═══════════════
echo ""
printf "${W}"
cat << DONE
  ╔══════════════════════════════════════════════╗
  ║           发版完成                           ║
  ╠══════════════════════════════════════════════╣
  ║  版本: ${TAG}                                  ║
  ║  更新包: ${UPDATE_SIZE}                              ║
  ╚══════════════════════════════════════════════╝
DONE
printf "${N}"
echo ""
echo "  Release: https://github.com/${REPO}/releases/tag/${TAG}"
echo ""
