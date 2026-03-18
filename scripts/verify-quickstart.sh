#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

DASHBOARD_URL="http://127.0.0.1:8091"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/verify-quickstart.log"

exec > >(tee "$LOG_FILE") 2>&1

echo "[verify] root=$ROOT_DIR"
echo "[verify] dashboard=$DASHBOARD_URL"

if [[ ! -f .env ]]; then
  echo "[FAIL] .env 不存在，请先执行: cp .env.example .env"
  exit 1
fi

require_non_empty() {
  local key="$1"
  local value
  value="$(grep -E "^${key}=" .env | head -n1 | cut -d'=' -f2- || true)"
  if [[ -z "${value// }" ]]; then
    echo "[FAIL] 缺少必填环境变量: $key"
    exit 1
  fi
  echo "[OK] $key 已配置"
}

require_one_of() {
  local found=0
  for key in "$@"; do
    local value
    value="$(grep -E "^${key}=" .env | head -n1 | cut -d'=' -f2- || true)"
    if [[ -n "${value// }" ]]; then
      found=1
      echo "[OK] 网关模型 Key 已配置: $key"
      break
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    echo "[FAIL] 网关模型 Key 未配置（至少设置一个）：$*"
    exit 1
  fi
}

require_non_empty "AUTH_PASSWORD"
require_non_empty "XIANYU_COOKIE_1"
require_one_of "ANTHROPIC_API_KEY" "OPENAI_API_KEY" "MOONSHOT_API_KEY" "MINIMAX_API_KEY" "ZAI_API_KEY" "CUSTOM_GATEWAY_API_KEY"

if [[ -x "$ROOT_DIR/.venv312/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv312/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "[FAIL] 未找到可用 Python（需要 3.12+）"
  exit 1
fi

echo "[verify] python=$PYTHON_BIN"

if lsof -iTCP:8091 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[warn] 8091 已被占用，尝试复用现有服务"
else
  echo "[step] 启动 dashboard 服务"
  "$PYTHON_BIN" -m src.dashboard_server --host 127.0.0.1 --port 8091 >/tmp/xianyu-dashboard.log 2>&1 &
  DASH_PID=$!
  trap 'if [[ -n "${DASH_PID:-}" ]] && kill -0 "$DASH_PID" >/dev/null 2>&1; then kill "$DASH_PID"; fi' EXIT
  sleep 3
fi

echo "[step] 校验 dashboard /healthz"
HEALTH_JSON="$(curl -fsS "$DASHBOARD_URL/healthz")"
echo "[OK] healthz=$HEALTH_JSON"

echo "[step] 校验 Cookie 配置已被 dashboard 读取"
COOKIE_JSON="$(curl -fsS "$DASHBOARD_URL/api/get-cookie")"
echo "[OK] api/get-cookie=$COOKIE_JSON"

if ! echo "$COOKIE_JSON" | grep -q '"success": true'; then
  echo "[FAIL] Cookie 未就绪，请更新 .env 中 XIANYU_COOKIE_1"
  exit 1
fi

echo "[PASS] Quickstart smoke 验证通过"
echo "[PASS] 打开 $DASHBOARD_URL 即可进行首次配置与验证"
