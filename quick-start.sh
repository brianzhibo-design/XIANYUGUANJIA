#!/usr/bin/env bash
# 闲鱼管家 - 快速启动 (交互式引导)
# 用法: bash quick-start.sh
# 支持离线部署（检测 vendor/ 目录）和在线部署（自动镜像源切换）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

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

clear 2>/dev/null || true
echo ""
printf "${W}"
cat << 'BANNER'
  ╔══════════════════════════════════════════════╗
  ║         闲鱼管家 · 快速启动引导             ║
  ║       Xianyu OpenClaw Quick Start           ║
  ╚══════════════════════════════════════════════╝
BANNER
printf "${N}"
echo ""

# ═══════════════ 0. 部署模式检测 ═══════════════
VENDOR_DIR="$SCRIPT_DIR/vendor"
OFFLINE_MODE=0

if [ -d "$VENDOR_DIR/pip-packages" ] && [ -d "$VENDOR_DIR/installers" ]; then
  OFFLINE_MODE=1
  printf "${G}  [模式]${N} 检测到 vendor/ 离线部署包，使用离线安装\n"
else
  printf "${C}  [模式]${N} 在线安装模式\n"
fi

# 检测平台
PLATFORM_DIR=""
if [[ "$OSTYPE" == "darwin"* ]]; then
  PLATFORM_DIR="macos"
  PIP_PLATFORM_DIR="macos-arm64"
else
  PLATFORM_DIR="linux"
  PIP_PLATFORM_DIR="linux"
fi

# ═══════════════ 0.5 网络环境检测（仅在线模式） ═══════════════
USE_CN_MIRROR=0
PIP_MIRROR_ARGS=""
NPM_REGISTRY=""

if [ "$OFFLINE_MODE" -eq 0 ]; then
  if [ "${CHINA_MIRROR:-}" = "1" ] || [ "${CN_MIRROR:-}" = "1" ]; then
    USE_CN_MIRROR=1
  elif [ "${CHINA_MIRROR:-}" = "0" ] || [ "${CN_MIRROR:-}" = "0" ]; then
    USE_CN_MIRROR=0
  elif ! curl -s --max-time 3 https://pypi.org/ >/dev/null 2>&1; then
    USE_CN_MIRROR=1
  fi

  if [ "$USE_CN_MIRROR" -eq 1 ]; then
    PIP_MIRROR_ARGS="-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
    NPM_REGISTRY="https://registry.npmmirror.com"
    printf "${Y}  [镜像]${N} 检测到国内网络环境，已自动切换国内镜像源\n"
    info "pip  → mirrors.aliyun.com"
    info "npm  → registry.npmmirror.com"
    echo ""
    info "强制使用国际源: CHINA_MIRROR=0 bash quick-start.sh"
  else
    printf "${G}  [镜像]${N} 使用国际源 (可设 CHINA_MIRROR=1 强制使用国内源)\n"
  fi
fi
echo ""

# ═══════════════ 1. 基础环境安装 ═══════════════
printf "${B}[1/7] 安装基础环境${N}\n"

HAS_PY=0; HAS_NODE=0; HAS_NPM=0

# -- Python 检测与安装 --
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  ok "Python $PY_VER"
  HAS_PY=1
else
  if [ "$OFFLINE_MODE" -eq 1 ]; then
    PKG_FILE=$(ls "$VENDOR_DIR/installers/$PLATFORM_DIR/python-"*.pkg 2>/dev/null | head -1)
    if [ -n "$PKG_FILE" ] && [[ "$OSTYPE" == "darwin"* ]]; then
      info "从离线包安装 Python..."
      sudo installer -pkg "$PKG_FILE" -target / && HAS_PY=1
      if [ "$HAS_PY" -eq 1 ]; then
        # macOS pkg 安装后需要刷新 PATH
        export PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH"
        ok "Python 已从离线包安装"
      fi
    fi
  else
    if [[ "$OSTYPE" == "darwin"* ]]; then
      if command -v brew &>/dev/null; then
        info "通过 Homebrew 安装 Python..."
        brew install python@3.12 && HAS_PY=1 && ok "Python 已通过 brew 安装"
      else
        info "安装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || true
        brew install python@3.12 && HAS_PY=1 && ok "Python 已通过 brew 安装"
      fi
    elif command -v apt-get &>/dev/null; then
      info "通过 apt 安装 Python..."
      sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-venv python3-pip && HAS_PY=1
      ok "Python 已通过 apt 安装"
    elif command -v dnf &>/dev/null; then
      info "通过 dnf 安装 Python..."
      sudo dnf install -y python3 python3-pip && HAS_PY=1
      ok "Python 已通过 dnf 安装"
    fi
  fi
  if [ "$HAS_PY" -eq 0 ]; then
    fail "Python3 安装失败 (需要 3.10+)"
    info "请手动安装: https://python.org/downloads/"
  fi
fi

# -- Node.js 检测与安装 --
if command -v node &>/dev/null; then
  ok "Node.js $(node -v)"
  HAS_NODE=1
else
  if [ "$OFFLINE_MODE" -eq 1 ]; then
    PKG_FILE=$(ls "$VENDOR_DIR/installers/$PLATFORM_DIR/node-"*.pkg 2>/dev/null | head -1)
    if [ -n "$PKG_FILE" ] && [[ "$OSTYPE" == "darwin"* ]]; then
      info "从离线包安装 Node.js..."
      sudo installer -pkg "$PKG_FILE" -target / && HAS_NODE=1
      [ "$HAS_NODE" -eq 1 ] && ok "Node.js 已从离线包安装"
    fi
  else
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &>/dev/null; then
      info "通过 Homebrew 安装 Node.js..."
      brew install node && HAS_NODE=1 && ok "Node.js 已通过 brew 安装"
    elif command -v apt-get &>/dev/null; then
      info "通过 apt 安装 Node.js..."
      sudo apt-get install -y -qq nodejs npm && HAS_NODE=1
      ok "Node.js 已通过 apt 安装"
    fi
  fi
  if [ "$HAS_NODE" -eq 0 ]; then
    fail "Node.js 安装失败 (需要 18+)"
    info "请手动安装: https://nodejs.org/"
  fi
fi

command -v npm &>/dev/null && HAS_NPM=1

if [ "$HAS_PY" -eq 0 ] || [ "$HAS_NODE" -eq 0 ]; then
  echo ""
  fail "缺少必要依赖，请安装后重新运行"
  exit 1
fi
echo ""

# ═══════════════ 2. 项目依赖安装 ═══════════════
printf "${B}[2/7] 安装项目依赖${N}\n"

# -- Python venv --
if [ ! -d ".venv" ]; then
  info "创建 Python 虚拟环境..."
  python3 -m venv .venv
  ok "虚拟环境已创建"
else
  ok "虚拟环境已存在"
fi

source .venv/bin/activate

# -- pip 依赖 --
if [ ! -f ".venv/.deps_ok" ] || [ requirements.txt -nt ".venv/.deps_ok" ]; then
  if [ "$OFFLINE_MODE" -eq 1 ] && [ -d "$VENDOR_DIR/pip-packages/$PIP_PLATFORM_DIR" ]; then
    info "从离线包安装 Python 依赖..."
    pip install --no-index --find-links "$VENDOR_DIR/pip-packages/$PIP_PLATFORM_DIR/" -r requirements.txt -q && touch .venv/.deps_ok
    ok "Python 依赖安装完成 (离线)"
  else
    info "安装 Python 依赖 (首次约 2 分钟)..."
    pip install -q -r requirements.txt $PIP_MIRROR_ARGS && touch .venv/.deps_ok
    ok "Python 依赖安装完成"
  fi
else
  ok "Python 依赖已是最新"
fi

# -- npm 前端依赖 --
NPM_INSTALL_ARGS="--silent"
if [ -n "$NPM_REGISTRY" ]; then
  NPM_INSTALL_ARGS="$NPM_INSTALL_ARGS --registry=$NPM_REGISTRY"
fi

if [ ! -d "client/node_modules" ]; then
  if [ "$OFFLINE_MODE" -eq 1 ] && [ -d "$VENDOR_DIR/npm-cache" ]; then
    info "从离线缓存安装前端依赖..."
    (cd client && npm install --prefer-offline --cache "$VENDOR_DIR/npm-cache" --silent 2>/dev/null)
    ok "前端依赖安装完成 (离线)"
  else
    info "安装前端依赖 (首次约 1 分钟)..."
    (cd client && npm install $NPM_INSTALL_ARGS 2>/dev/null)
    ok "前端依赖安装完成"
  fi
else
  ok "前端依赖已存在"
fi
echo ""

# ═══════════════ 3. 配置检查 ═══════════════
printf "${B}[3/7] 检查配置${N}\n"

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    warn ".env 已从模板创建，请稍后编辑填入 Cookie"
  else
    warn "未找到 .env 文件"
  fi
else
  ok ".env 配置文件存在"
fi

if [ -f "config/config.yaml" ]; then
  ok "config/config.yaml 存在"
else
  if [ -f "config/config.example.yaml" ]; then
    cp config/config.example.yaml config/config.yaml
    warn "config.yaml 已从模板创建"
  fi
fi

if [ -f "data/system_config.json" ]; then
  HAS_AI_KEY=$(python3 -c "
import json
try:
  d=json.load(open('data/system_config.json'))
  k=d.get('ai',{}).get('api_key','')
  print('yes' if k and len(k)>10 else 'no')
except: print('no')
" 2>/dev/null || echo "no")
  if [ "$HAS_AI_KEY" = "yes" ]; then
    ok "AI API Key 已配置 (system_config.json)"
  else
    warn "AI API Key 未配置 (可在管理面板 → 系统配置 中设置)"
  fi
else
  warn "system_config.json 不存在 (首次启动后自动生成)"
fi

# 检测备份数据（设备迁移场景）
if [ -d "data/backups" ] && [ "$(ls -A data/backups/ 2>/dev/null)" ]; then
  LATEST_BACKUP=$(ls -1d data/backups/*/ 2>/dev/null | tail -1)
  if [ -n "$LATEST_BACKUP" ]; then
    warn "检测到备份数据: $LATEST_BACKUP"
    info "如需恢复，运行: bash scripts/restore_data.sh $LATEST_BACKUP"
  fi
fi
echo ""

# ═══════════════ 4. 启动服务 ═══════════════
printf "${B}[4/7] 启动服务${N}\n"

cleanup() {
  echo ""
  warn "正在停止所有服务..."
  kill $PY_PID 2>/dev/null || true
  kill $FE_PID 2>/dev/null || true
  wait 2>/dev/null || true
  ok "所有服务已停止"
}
trap cleanup EXIT INT TERM

for port in 8091 5173 3001; do
  lsof -ti :$port 2>/dev/null | xargs kill -9 2>/dev/null || true
done
sleep 1

info "启动 Python 后端 (端口 8091)..."
python3 -m src.dashboard_server --port 8091 &
PY_PID=$!

info "启动 React 前端 (端口 5173)..."
(cd client && npx vite --host 2>/dev/null) &
FE_PID=$!

sleep 4

PY_OK=0; FE_OK=0
curl -s --max-time 3 http://localhost:8091/ >/dev/null 2>&1 && PY_OK=1
curl -s --max-time 3 http://localhost:5173/ >/dev/null 2>&1 && FE_OK=1

[ "$PY_OK" -eq 1 ] && ok "Python 后端启动成功" || warn "Python 后端启动中..."
[ "$FE_OK" -eq 1 ] && ok "React 前端启动成功" || warn "React 前端启动中..."
echo ""

# ═══════════════ 5. 外部服务引导 ═══════════════
printf "${B}[5/7] 外部服务配置引导${N}\n"

# CookieCloud 配置检测
CC_CONFIGURED=0
if [ -f "data/system_config.json" ]; then
  CC_CONFIGURED=$(python3 -c "
import json
try:
  d=json.load(open('data/system_config.json'))
  cc=d.get('cookie_cloud',{})
  uuid=cc.get('cookie_cloud_uuid','')
  pwd=cc.get('cookie_cloud_password','')
  print('1' if uuid and pwd else '0')
except: print('0')
" 2>/dev/null || echo "0")
fi

if [ "$CC_CONFIGURED" = "1" ]; then
  ok "CookieCloud 已配置 (Cookie 秒级自动同步)"
else
  warn "CookieCloud 未配置 (推荐配置，实现 Cookie 自动同步)"
  info "服务端已内置，无需额外部署。只需安装浏览器扩展:"
  if [ "$OFFLINE_MODE" -eq 1 ] && [ -f "$VENDOR_DIR/extensions/cookiecloud.crx" ]; then
    info "  离线安装: 打开 Chrome → 扩展管理 → 拖入 vendor/extensions/cookiecloud.crx"
  else
    info "  Chrome: https://chromewebstore.google.com/detail/cookiecloud/ffjiejobkoibkjlhjnlgmcnnigeelbdl"
    info "  Edge:   https://microsoftedge.microsoft.com/addons/detail/cookiecloud/bkifenclicgpjhgijmepkiielkeondlg"
  fi
  info "安装后在管理面板 → 系统配置 → CookieCloud 中填入 UUID 和密码"
fi

# BitBrowser 检测
BB_REACHABLE=0
curl -s --max-time 1 http://127.0.0.1:54345/ >/dev/null 2>&1 && BB_REACHABLE=1

if [ "$BB_REACHABLE" -eq 1 ]; then
  ok "BitBrowser 指纹浏览器已运行 (可在管理面板配置 browser_id)"
else
  info "BitBrowser 指纹浏览器未检测到 (可选功能，用于降低风控检测)"
  info "如需使用，请从 https://www.bitbrowser.net 下载安装"
  info "安装后在管理面板 → 系统配置 → 滑块验证 中配置"
fi
echo ""

# ═══════════════ 6. 系统诊断 ═══════════════
printf "${B}[6/7] 系统诊断${N}\n"
python3 -m src.cli doctor --skip-quote 2>/dev/null | head -20 || warn "诊断跳过 (服务启动中)"
echo ""

# ═══════════════ 7. 启动完成 ═══════════════
printf "${B}[7/7] 启动完成${N}\n"
echo ""
printf "${W}"
cat << 'INFO'
  ┌──────────────────────────────────────────────┐
  │  管理面板:     http://localhost:5173         │
  │  Python API:   http://localhost:8091         │
  │  对话沙盒:     管理面板 → 消息 → 对话沙盒   │
  └──────────────────────────────────────────────┘
INFO
printf "${N}"
echo ""
printf "${Y}  首次使用指南:${N}\n"
info "1. 打开 http://localhost:5173 进入管理面板"
info "2. 账户页 → 粘贴闲鱼 Cookie (或点击自动获取)"
info "3. 系统配置 → 配置 AI (推荐百炼千问 Qwen)"
info "4. 系统配置 → CookieCloud → 配置自动同步 (推荐)"
info "5. 消息页 → 对话沙盒测试自动回复效果"
info "6. 确认无误后开启自动回复"
echo ""
printf "${C}  按 Ctrl+C 停止所有服务${N}\n"
echo ""

wait
