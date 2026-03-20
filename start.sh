#!/usr/bin/env bash
# 闲鱼管家 - 服务启动脚本
# 由 update.sh / 手动执行；必须启动 dashboard_server（8091），工作台与 /api/health 才可用。
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

mkdir -p logs

# 优先使用项目内 venv 的 Python（不依赖交互式 activate）
PY=""
for candidate in \
  "$PROJECT_ROOT/.venv/bin/python3" \
  "$PROJECT_ROOT/.venv/bin/python" \
  "$PROJECT_ROOT/venv/bin/python3" \
  "$PROJECT_ROOT/venv/bin/python"; do
  if [ -x "$candidate" ]; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PY=python3
  else
    PY=python
  fi
fi

DASH_PORT="${XIANYU_DASHBOARD_PORT:-8091}"

echo "[>>] 启动 Dashboard (端口 ${DASH_PORT})..."
echo "     使用: $PY -m src.dashboard_server"
"$PY" -m src.dashboard_server --port "$DASH_PORT" >> logs/backend.log 2>&1 &
echo "[OK] 后端 PID: $!"

# 仅当没有构建产物时启动 Vite（开发态）；更新包通常含 client/dist，只需 8091
if [ ! -d "client/dist" ] && command -v npm >/dev/null 2>&1 && [ -f "client/package.json" ]; then
  echo "[>>] 未找到 client/dist，启动前端开发服务器 (5173)..."
  (cd client && npm run dev >> ../logs/frontend.log 2>&1) &
  echo "[OK] 前端开发服务器已启动"
fi

echo "[OK] 服务已启动"
