#!/usr/bin/env bash
# 闲鱼管家 - 服务启动脚本
# 由 update.sh 在更新完成后自动调用，也可手动执行
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

mkdir -p logs

# Start backend
echo "[>>] 启动后端 (端口 8091)..."
python -m src.main >> logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "[OK] 后端 PID: $BACKEND_PID"

# Start frontend dev server if node is available and client/dist doesn't exist
if [ ! -d "client/dist" ] && command -v npm >/dev/null 2>&1; then
  echo "[>>] 启动前端开发服务器 (端口 5173)..."
  (cd client && npm run dev >> ../logs/frontend.log 2>&1) &
  echo "[OK] 前端开发服务器已启动"
fi

echo "[OK] 服务已启动"
