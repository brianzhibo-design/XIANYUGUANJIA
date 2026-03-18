#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 从 Finder 双击 .command 启动时 PATH 不完整，补充常见路径
for p in /opt/homebrew/bin /opt/homebrew/sbin /usr/local/bin "$HOME/.nvm/versions/node"/*/bin; do
  [ -d "$p" ] && case ":$PATH:" in *:"$p":*) ;; *) export PATH="$p:$PATH" ;; esac
done
# 加载 nvm（如果存在）
[ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh" 2>/dev/null || true

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "========================================="
echo "  闲鱼管家 - 一键启动"
echo "========================================="
echo ""

# 0. 网络环境检测 - 自动切换国内镜像源
USE_CN_MIRROR=0
PIP_MIRROR_ARGS=""
NPM_REGISTRY_ARGS=""

if [ "${CHINA_MIRROR:-}" = "1" ] || [ "${CN_MIRROR:-}" = "1" ]; then
  USE_CN_MIRROR=1
elif [ "${CHINA_MIRROR:-}" = "0" ] || [ "${CN_MIRROR:-}" = "0" ]; then
  USE_CN_MIRROR=0
elif ! curl -s --max-time 3 https://pypi.org/ >/dev/null 2>&1; then
  USE_CN_MIRROR=1
fi

if [ "$USE_CN_MIRROR" -eq 1 ]; then
  PIP_MIRROR_ARGS="-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
  NPM_REGISTRY_ARGS="--registry=https://registry.npmmirror.com"
  info "国内网络环境，已切换国内镜像源"
fi

# 1. 检查 Python
if ! command -v python3 &>/dev/null; then
  fail "未找到 python3，请先安装 Python 3.10+"
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Python 版本: $PY_VER"

# 2. 检查 Node.js (Vite 前端需要)
if ! command -v node &>/dev/null; then
  fail "未找到 node, 请先安装 Node.js 18+"
fi

NODE_VER="$(node -v 2>/dev/null || echo unknown)"
info "Node.js 版本: ${NODE_VER}"

# 3. 创建 .env（如不存在）
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    warn ".env 文件不存在，已从 .env.example 创建。请编辑 .env 填入实际配置。"
  else
    fail "未找到 .env 和 .env.example"
  fi
else
  info ".env 已存在"
fi

# 3.5 创建 config.yaml（如不存在）
if [ ! -f "config/config.yaml" ]; then
  if [ -f "config/config.example.yaml" ]; then
    mkdir -p config
    cp config/config.example.yaml config/config.yaml
    info "config.yaml 已从模板创建"
  fi
fi

# 4. 创建 Python 虚拟环境并安装依赖
if [ ! -d ".venv" ]; then
  info "创建 Python 虚拟环境..."
  python3 -m venv .venv
fi

source .venv/bin/activate
info "Python 虚拟环境已激活"

if [ ! -f ".venv/.deps_installed" ] || [ requirements.txt -nt ".venv/.deps_installed" ]; then
  info "安装 Python 依赖..."
  pip install -q -r requirements.txt $PIP_MIRROR_ARGS
  touch .venv/.deps_installed
  info "Python 依赖安装完成"
else
  info "Python 依赖已是最新"
fi

# 5. 安装前端依赖（Vite 需要）
if [ ! -d "client/node_modules" ]; then
  info "安装 React 前端依赖..."
  (cd client && npm install --silent $NPM_REGISTRY_ARGS)
fi

# 5.5 确保 data/ 目录存在
mkdir -p data

info "所有依赖就绪"

# 6. 清理被占用端口
for port in 8091 5173; do
  if lsof -ti :"$port" >/dev/null 2>&1; then
    warn "端口 $port 被占用，正在释放..."
    lsof -ti :"$port" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
done

# 7. 启动服务
echo ""
echo "========================================="
echo "  启动所有服务"
echo "========================================="
echo ""

cleanup() {
  echo ""
  warn "正在停止所有服务..."
  kill $PY_PID 2>/dev/null || true
  kill $CLIENT_PID 2>/dev/null || true
  wait 2>/dev/null || true
  info "所有服务已停止"
}
trap cleanup EXIT INT TERM

# Python 后端
info "启动 Python 后端 (端口 8091)..."
python3 -m src.dashboard_server --port 8091 &
PY_PID=$!

# React 前端（Vite dev server）
info "启动 React 前端 (端口 5173)..."
(cd client && npx vite --host) &
CLIENT_PID=$!

sleep 2
echo ""
echo "========================================="
echo "  所有服务已启动"
echo "========================================="
echo ""
info "管理面板:    http://localhost:5173"
info "Python 后端: http://localhost:8091"
echo ""
info "按 Ctrl+C 停止所有服务"
echo ""

wait
