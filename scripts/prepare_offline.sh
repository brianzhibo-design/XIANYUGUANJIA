#!/usr/bin/env bash
# 闲鱼管家 - 离线部署包准备脚本
# 在有网络的设备上运行，将所有依赖下载到 vendor/ 目录
# 然后通过 U 盘拷贝整个项目到新设备，运行 quick-start.sh 即可离线部署
#
# 用法:
#   bash scripts/prepare_offline.sh                  # 下载当前平台
#   bash scripts/prepare_offline.sh --platform all   # 下载 macOS + Windows 双平台
#   bash scripts/prepare_offline.sh --platform windows  # 仅下载 Windows
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

R='\033[0;31m'
G='\033[0;32m'
Y='\033[1;33m'
B='\033[1;34m'
C='\033[0;36m'
W='\033[1;37m'
N='\033[0m'

ok()   { printf "${G}  [OK]${N} %s\n" "$1"; }
warn() { printf "${Y}  [!!]${N} %s\n" "$1"; }
fail() { printf "${R}  [NG]${N} %s\n" "$1"; }
info() { printf "${C}  -->  ${N}%s\n" "$1"; }

VENDOR_DIR="$PROJECT_ROOT/vendor"
PYTHON_VER="3.12.8"
NODE_VER="v20.18.1"
TARGET_PYVER="3.12"

# ═══════════════ 参数解析 ═══════════════
PLATFORM="current"
for arg in "$@"; do
  case "$arg" in
    --platform=*) PLATFORM="${arg#*=}" ;;
    --platform)   shift_next=1 ;;
    *)
      if [ "${shift_next:-}" = "1" ]; then
        PLATFORM="$arg"
        shift_next=0
      fi
      ;;
  esac
done

CURRENT_OS=""
if [[ "$OSTYPE" == "darwin"* ]]; then
  CURRENT_OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
  CURRENT_OS="windows"
else
  CURRENT_OS="linux"
fi

PREP_MACOS=0
PREP_WINDOWS=0
case "$PLATFORM" in
  all)     PREP_MACOS=1; PREP_WINDOWS=1 ;;
  macos)   PREP_MACOS=1 ;;
  windows) PREP_WINDOWS=1 ;;
  current)
    [ "$CURRENT_OS" = "macos" ] && PREP_MACOS=1
    [ "$CURRENT_OS" = "windows" ] && PREP_WINDOWS=1
    [ "$CURRENT_OS" = "linux" ] && { PREP_MACOS=1; warn "Linux 主机默认准备 macOS 包，Windows 需在 Windows 上单独 prepare"; }
    ;;
  *) fail "未知平台: $PLATFORM (可选: all, macos, windows, current)"; exit 1 ;;
esac

# ═══════════════ Banner ═══════════════
clear 2>/dev/null || true
echo ""
printf "${W}"
cat << 'BANNER'
  ╔══════════════════════════════════════════════╗
  ║      闲鱼管家 · 离线部署包准备工具          ║
  ║    Xianyu OpenClaw Offline Prep Tool        ║
  ╚══════════════════════════════════════════════╝
BANNER
printf "${N}"
echo ""
info "目标平台: macOS=$PREP_MACOS Windows=$PREP_WINDOWS"
info "输出目录: $VENDOR_DIR"
echo ""

# ═══════════════ 0. 环境检查 ═══════════════
printf "${B}[1/5] 环境检查${N}\n"

command -v python3 &>/dev/null || { fail "需要 python3"; exit 1; }
command -v pip3 &>/dev/null || command -v pip &>/dev/null || { fail "需要 pip"; exit 1; }
command -v curl &>/dev/null || { fail "需要 curl"; exit 1; }
command -v npm &>/dev/null || { fail "需要 npm (用于缓存前端依赖)"; exit 1; }

PIP_CMD="pip3"
command -v pip3 &>/dev/null || PIP_CMD="pip"

ok "基础工具就绪"
echo ""

# ═══════════════ 1. 创建目录结构 ═══════════════
printf "${B}[2/5] 创建目录结构${N}\n"

mkdir -p "$VENDOR_DIR"/{installers/macos,installers/windows,pip-packages/macos-arm64,pip-packages/windows-amd64,npm-cache,extensions}

ok "vendor/ 目录结构已创建"
echo ""

# ═══════════════ 2. 下载 Python / Node 安装包 ═══════════════
printf "${B}[3/5] 下载 Python / Node 安装包${N}\n"

download_if_missing() {
  local url="$1" dest="$2" label="$3"
  if [ -f "$dest" ]; then
    ok "$label (已存在，跳过)"
    return 0
  fi
  info "下载 $label ..."
  if curl -L --progress-bar -o "$dest.tmp" "$url"; then
    mv "$dest.tmp" "$dest"
    local size; size=$(du -h "$dest" | cut -f1)
    ok "$label ($size)"
  else
    rm -f "$dest.tmp"
    warn "$label 下载失败: $url"
    return 1
  fi
}

if [ "$PREP_MACOS" -eq 1 ]; then
  download_if_missing \
    "https://www.python.org/ftp/python/${PYTHON_VER}/python-${PYTHON_VER}-macos11.pkg" \
    "$VENDOR_DIR/installers/macos/python-${PYTHON_VER}-macos11.pkg" \
    "Python ${PYTHON_VER} macOS installer"

  download_if_missing \
    "https://npmmirror.com/mirrors/node/${NODE_VER}/node-${NODE_VER}.pkg" \
    "$VENDOR_DIR/installers/macos/node-${NODE_VER}.pkg" \
    "Node.js ${NODE_VER} macOS installer"
fi

if [ "$PREP_WINDOWS" -eq 1 ]; then
  download_if_missing \
    "https://www.python.org/ftp/python/${PYTHON_VER}/python-${PYTHON_VER}-amd64.exe" \
    "$VENDOR_DIR/installers/windows/python-${PYTHON_VER}-amd64.exe" \
    "Python ${PYTHON_VER} Windows installer"

  download_if_missing \
    "https://npmmirror.com/mirrors/node/${NODE_VER}/node-${NODE_VER}-x64.msi" \
    "$VENDOR_DIR/installers/windows/node-${NODE_VER}-x64.msi" \
    "Node.js ${NODE_VER} Windows installer"
fi

echo ""

# ═══════════════ 3. 下载 pip 包（含完整依赖链） ═══════════════
printf "${B}[4/5] 下载 Python 依赖包${N}\n"

REQ_FILE="$PROJECT_ROOT/requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
  fail "requirements.txt 不存在"
  exit 1
fi

download_pip_packages() {
  local platform_tag="$1" dest_dir="$2" label="$3"

  if [ -d "$dest_dir" ] && [ "$(ls -A "$dest_dir" 2>/dev/null)" ]; then
    local count
    count=$(find "$dest_dir" -maxdepth 1 \( -name "*.whl" -o -name "*.tar.gz" -o -name "*.zip" \) | wc -l | tr -d ' ')
    if [ "$count" -gt 10 ]; then
      ok "$label (已存在 ${count} 个包，跳过。删除目录可重新下载)"
      return 0
    fi
  fi

  info "下载 $label (逐包下载, wheel 优先)..."

  local succeeded=0 failed=0
  while IFS= read -r pkg_line; do
    pkg_line=$(echo "$pkg_line" | sed 's/#.*//' | tr -d ' ')
    [ -z "$pkg_line" ] && continue

    local pkg_name
    pkg_name=$(echo "$pkg_line" | sed 's/[>=<\[].*//' | tr '[:upper:]' '[:lower:]' | tr '-' '_')

    if $PIP_CMD download "$pkg_line" \
      --platform "$platform_tag" \
      --python-version "$TARGET_PYVER" \
      --only-binary=:all: \
      --no-deps \
      -d "$dest_dir/" 2>/dev/null; then
      succeeded=$((succeeded + 1))
    else
      if $PIP_CMD download "$pkg_line" --no-binary=:all: --no-deps -d "$dest_dir/" 2>/dev/null; then
        succeeded=$((succeeded + 1))
      else
        warn "  跳过: $pkg_line (无可用 wheel/sdist)"
        failed=$((failed + 1))
      fi
    fi
  done < "$REQ_FILE"

  # 补充下载传递依赖（如 pydantic-core、typing-extensions 等）
  info "补充传递依赖..."
  # 排除无 wheel 的纯 sdist 包，只下载有 wheel 的包的传递依赖
  local temp_req; temp_req=$(mktemp)
  grep -v "^#" "$REQ_FILE" | grep -v "^$" | grep -iv "oss2" > "$temp_req" || true
  $PIP_CMD download -r "$temp_req" \
    --platform "$platform_tag" \
    --python-version "$TARGET_PYVER" \
    --only-binary=:all: \
    -d "$dest_dir/" 2>&1 | grep -E "Saved|already" || true
  rm -f "$temp_req"

  local final_count
  final_count=$(find "$dest_dir" -maxdepth 1 \( -name "*.whl" -o -name "*.tar.gz" -o -name "*.zip" \) | wc -l | tr -d ' ')
  local total_size
  total_size=$(du -sh "$dest_dir" | cut -f1)
  ok "$label 完成 (${final_count} 个包, ${total_size}, ${failed} 个跳过)"
}

if [ "$PREP_MACOS" -eq 1 ]; then
  download_pip_packages "macosx_11_0_arm64" "$VENDOR_DIR/pip-packages/macos-arm64" "macOS ARM64 pip 依赖"
fi

if [ "$PREP_WINDOWS" -eq 1 ]; then
  download_pip_packages "win_amd64" "$VENDOR_DIR/pip-packages/windows-amd64" "Windows x64 pip 依赖"
fi

echo ""

# ═══════════════ 4. 缓存 npm 前端依赖 ═══════════════
printf "${B}[5/5] 缓存前端依赖${N}\n"

NPM_CACHE_DIR="$VENDOR_DIR/npm-cache"

if [ -d "$PROJECT_ROOT/client/node_modules" ] && [ "$(ls -A "$PROJECT_ROOT/client/node_modules" 2>/dev/null)" ]; then
  ok "client/node_modules 已存在，将作为离线缓存源"
fi

if [ -d "$NPM_CACHE_DIR" ] && [ "$(ls -A "$NPM_CACHE_DIR" 2>/dev/null)" ]; then
  ok "npm 缓存已存在 (跳过)"
else
  info "安装前端依赖并填充 npm 缓存..."
  (cd "$PROJECT_ROOT/client" && npm install --cache "$NPM_CACHE_DIR" --prefer-offline 2>/dev/null)
  local_size=$(du -sh "$NPM_CACHE_DIR" 2>/dev/null | cut -f1)
  ok "npm 缓存已填充 (${local_size})"
fi

echo ""

# CookieCloud 扩展引导
echo ""
info "CookieCloud 浏览器扩展需手动下载放入 vendor/extensions/:"
info "  Chrome: https://chromewebstore.google.com/detail/cookiecloud/ffjiejobkoibkjlhjnlgmcnnigeelbdl"
info "  Edge:   https://microsoftedge.microsoft.com/addons/detail/cookiecloud/bkifenclicgpjhgijmepkiielkeondlg"
info "  GitHub: https://github.com/easychen/CookieCloud/releases"
info "  下载后放到: vendor/extensions/cookiecloud.crx"

echo ""

# ═══════════════ 生成 manifest ═══════════════
MANIFEST="$VENDOR_DIR/manifest.json"
python3 -c "
import json, os, hashlib, datetime

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

vendor = '$VENDOR_DIR'
files = {}
for root, dirs, fnames in os.walk(vendor):
    for fn in fnames:
        fp = os.path.join(root, fn)
        rel = os.path.relpath(fp, vendor)
        if rel == 'manifest.json':
            continue
        size = os.path.getsize(fp)
        if size > 0:
            files[rel] = {
                'size': size,
                'sha256': file_sha256(fp) if size < 500_000_000 else 'skipped-large-file',
            }

manifest = {
    'version': '1.0',
    'created': datetime.datetime.now().isoformat(),
    'python_version': '$PYTHON_VER',
    'node_version': '$NODE_VER',
    'target_python': '$TARGET_PYVER',
    'platforms': {
        'macos': bool($PREP_MACOS),
        'windows': bool($PREP_WINDOWS),
    },
    'file_count': len(files),
    'files': files,
}

with open(os.path.join(vendor, 'manifest.json'), 'w') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f'manifest.json: {len(files)} files tracked')
" 2>/dev/null && ok "manifest.json 已生成" || warn "manifest.json 生成失败"

# ═══════════════ 完成 ═══════════════
echo ""
TOTAL_SIZE=$(du -sh "$VENDOR_DIR" 2>/dev/null | cut -f1)
printf "${W}"
cat << DONE
  ╔══════════════════════════════════════════════╗
  ║           离线部署包准备完成                 ║
  ╠══════════════════════════════════════════════╣
  ║  总大小: $(printf '%-36s' "$TOTAL_SIZE")║
  ║  位置:   vendor/                            ║
  ╚══════════════════════════════════════════════╝
DONE
printf "${N}"
echo ""
printf "${Y}  下一步:${N}\n"
info "1. 将整个项目目录拷贝到 U 盘"
info "2. 在新设备上从 U 盘拷贝到本地"
info "3. 运行 bash quick-start.sh (macOS/Linux)"
info "   或   start.bat (Windows)"
info "4. 脚本会自动检测 vendor/ 并走离线安装路径"
if [ "$PREP_MACOS" -eq 1 ] && [ "$PREP_WINDOWS" -eq 0 ]; then
  echo ""
  warn "当前仅准备了 macOS 平台"
  info "如需 Windows 离线包，在 Windows 设备运行:"
  info "  scripts\\windows\\prepare_offline.bat"
  info "然后合并 vendor/ 目录"
fi
if [ "$PREP_WINDOWS" -eq 1 ] && [ "$PREP_MACOS" -eq 0 ]; then
  echo ""
  warn "当前仅准备了 Windows 平台"
  info "如需 macOS 离线包，在 macOS 设备运行:"
  info "  bash scripts/prepare_offline.sh --platform macos"
  info "然后合并 vendor/ 目录"
fi
echo ""
