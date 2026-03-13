#!/usr/bin/env bash
# 闲鱼管家 - 快速启动 (交互式引导)
# 用法: bash quick-start.sh
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

# ═══════════════ 1. 环境检查 ═══════════════
printf "${B}[1/5] 检查运行环境${N}\n"

HAS_PY=0; HAS_NODE=0; HAS_NPM=0

if command -v python3 &>/dev/null; then
  PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  ok "Python $PY_VER"
  HAS_PY=1
else
  fail "未安装 Python3 (需要 3.10+)"
  info "安装: brew install python3  或  https://python.org"
fi

if command -v node &>/dev/null; then
  ok "Node.js $(node -v)"
  HAS_NODE=1
else
  fail "未安装 Node.js (需要 18+)"
  info "安装: brew install node  或  https://nodejs.org"
fi

if command -v npm &>/dev/null; then
  ok "npm $(npm -v)"
  HAS_NPM=1
else
  fail "未安装 npm"
fi

if [ "$HAS_PY" -eq 0 ] || [ "$HAS_NODE" -eq 0 ]; then
  echo ""
  fail "缺少必要依赖，请先安装后重新运行"
  exit 1
fi
echo ""

# ═══════════════ 2. 依赖安装 ═══════════════
printf "${B}[2/5] 安装依赖${N}\n"

if [ ! -d ".venv" ]; then
  info "创建 Python 虚拟环境..."
  python3 -m venv .venv
  ok "虚拟环境已创建"
else
  ok "虚拟环境已存在"
fi

source .venv/bin/activate

if [ ! -f ".venv/.deps_ok" ] || [ requirements.txt -nt ".venv/.deps_ok" ]; then
  info "安装 Python 依赖 (首次约 2 分钟)..."
  pip install -q -r requirements.txt && touch .venv/.deps_ok
  ok "Python 依赖安装完成"
else
  ok "Python 依赖已是最新"
fi

if [ ! -d "client/node_modules" ]; then
  info "安装前端依赖 (首次约 1 分钟)..."
  (cd client && npm install --silent 2>/dev/null)
  ok "前端依赖安装完成"
else
  ok "前端依赖已存在"
fi

if [ ! -d "server/node_modules" ]; then
  info "安装 Node 后端依赖..."
  (cd server && npm install --silent 2>/dev/null)
  ok "Node 后端依赖安装完成"
else
  ok "Node 后端依赖已存在"
fi

if [ ! -f ".venv/.playwright_ok" ]; then
  info "安装 Playwright 浏览器 (首次约 150MB)..."
  playwright install chromium 2>/dev/null && touch .venv/.playwright_ok
  ok "Playwright 安装完成"
else
  ok "Playwright 已就绪"
fi
echo ""

# ═══════════════ 3. 配置检查 ═══════════════
printf "${B}[3/5] 检查配置${N}\n"

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

if [ -f "server/data/system_config.json" ]; then
  HAS_AI_KEY=$(python3 -c "
import json
try:
  d=json.load(open('server/data/system_config.json'))
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
echo ""

# ═══════════════ 4. 启动服务 ═══════════════
printf "${B}[4/5] 启动服务${N}\n"

cleanup() {
  echo ""
  warn "正在停止所有服务..."
  kill $PY_PID 2>/dev/null || true
  kill $FE_PID 2>/dev/null || true
  kill $ND_PID 2>/dev/null || true
  wait 2>/dev/null || true
  ok "所有服务已停止"
}
trap cleanup EXIT INT TERM

# 清理残留端口
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

info "启动 Node.js 后端 (端口 3001)..."
(cd server && node src/app.js 2>/dev/null) &
ND_PID=$!

sleep 4

PY_OK=0; FE_OK=0
curl -s --max-time 3 http://localhost:8091/ >/dev/null 2>&1 && PY_OK=1
curl -s --max-time 3 http://localhost:5173/ >/dev/null 2>&1 && FE_OK=1

[ "$PY_OK" -eq 1 ] && ok "Python 后端启动成功" || warn "Python 后端启动中..."
[ "$FE_OK" -eq 1 ] && ok "React 前端启动成功" || warn "React 前端启动中..."
echo ""

# ═══════════════ 5. 完成引导 ═══════════════
printf "${B}[5/5] 启动完成${N}\n"
echo ""
printf "${W}"
cat << 'INFO'
  ┌──────────────────────────────────────────────┐
  │  管理面板:     http://localhost:5173         │
  │  Python API:   http://localhost:8091         │
  │  Node.js API:  http://localhost:3001         │
  │  对话沙盒:     管理面板 → 消息 → 对话沙盒   │
  └──────────────────────────────────────────────┘
INFO
printf "${N}"
echo ""
printf "${Y}  首次使用指南:${N}\n"
info "1. 打开 http://localhost:5173 进入管理面板"
info "2. 账户页 → 粘贴闲鱼 Cookie (或点击自动获取)"
info "3. 系统配置 → 配置 AI (推荐百炼千问 Qwen)"
info "4. 消息页 → 对话沙盒测试自动回复效果"
info "5. 确认无误后开启自动回复"
echo ""
printf "${C}  按 Ctrl+C 停止所有服务${N}\n"
echo ""

wait
