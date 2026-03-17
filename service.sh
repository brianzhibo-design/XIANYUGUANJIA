#!/usr/bin/env bash
# ─────────────────────────────────────────────
#  闲鱼管家 · 统一服务管理
#  用法:
#    bash service.sh start     启动全部服务
#    bash service.sh stop      停止全部服务
#    bash service.sh restart   重启全部服务
#    bash service.sh status    查看服务状态
# ─────────────────────────────────────────────
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PID_DIR="$ROOT_DIR/.pids"
LOG_DIR="$ROOT_DIR/logs"
VENV_PY="$ROOT_DIR/.venv/bin/python3"

BACKEND_PORT=8091
FRONTEND_PORT=5173

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }

mkdir -p "$PID_DIR" "$LOG_DIR"

# ─── 工具函数 ───────────────────────────────

_read_pid() {
  local f="$PID_DIR/$1.pid"
  [ -f "$f" ] && cat "$f" || echo ""
}

_write_pid() {
  echo "$2" > "$PID_DIR/$1.pid"
}

_clear_pid() {
  rm -f "$PID_DIR/$1.pid"
}

_is_running() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

_kill_by_pid() {
  local name="$1" pid
  pid="$(_read_pid "$name")"
  if _is_running "$pid"; then
    kill "$pid" 2>/dev/null
    sleep 1
    _is_running "$pid" && kill -9 "$pid" 2>/dev/null
  fi
  _clear_pid "$name"
}

_read_daemon_pid() {
  local json_file="$ROOT_DIR/data/module_runtime/$1.json"
  if [ -f "$json_file" ]; then
    "$VENV_PY" -c "import json,sys;print(json.load(open(sys.argv[1])).get('pid',''))" "$json_file" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

_kill_presales() {
  local pid daemon_pid
  pid="$(_read_pid presales)"
  daemon_pid="$(_read_daemon_pid presales)"

  for p in $pid $daemon_pid; do
    if [ -n "$p" ] && _is_running "$p"; then
      kill "$p" 2>/dev/null
      sleep 1
      _is_running "$p" && kill -9 "$p" 2>/dev/null
    fi
  done
  _clear_pid presales
  pkill -f 'src\.cli module.*presales' 2>/dev/null || true
}

_kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti :"$port" 2>/dev/null || true)"
  [ -n "$pids" ] && echo "$pids" | xargs kill -9 2>/dev/null || true
}

_ensure_venv() {
  if [ ! -x "$VENV_PY" ]; then
    fail "未找到 venv Python: $VENV_PY"
    fail "请先运行 bash quick-start.sh 完成初始安装"
    exit 1
  fi
}

_check_http() {
  curl -sf --max-time 3 "http://localhost:$1$2" >/dev/null 2>&1
}

# ─── 启动 ───────────────────────────────────

do_start() {
  _ensure_venv
  log "启动全部服务..."
  echo ""

  # 1) 后端
  local be_pid
  be_pid="$(_read_pid backend)"
  if _is_running "$be_pid"; then
    ok "后端已在运行 (PID $be_pid, 端口 $BACKEND_PORT)"
  else
    _kill_port "$BACKEND_PORT"
    "$VENV_PY" -m src.dashboard_server --port "$BACKEND_PORT" >> "$LOG_DIR/backend.log" 2>&1 &
    _write_pid backend $!
    ok "后端已启动 (PID $!, 端口 $BACKEND_PORT)"
  fi

  # 2) 前端
  local fe_pid
  fe_pid="$(_read_pid frontend)"
  if _is_running "$fe_pid"; then
    ok "前端已在运行 (PID $fe_pid, 端口 $FRONTEND_PORT)"
  else
    _kill_port "$FRONTEND_PORT"
    (cd client && npx vite --host --port "$FRONTEND_PORT") >> "$LOG_DIR/frontend.log" 2>&1 &
    _write_pid frontend $!
    ok "前端已启动 (PID $!, 端口 $FRONTEND_PORT)"
  fi

  # 3) Presales daemon
  local ps_pid
  ps_pid="$(_read_pid presales)"
  if _is_running "$ps_pid"; then
    ok "Presales daemon 已在运行 (PID $ps_pid)"
  else
    pkill -f 'src.cli module.*presales' 2>/dev/null || true
    "$VENV_PY" -m src.cli module --action start --target presales --mode daemon \
      --interval 1.0 --limit 20 --claim-limit 10 >> "$LOG_DIR/presales.log" 2>&1 &
    _write_pid presales $!
    ok "Presales daemon 已启动 (PID $!)"
  fi

  echo ""
  sleep 2

  # 健康检查
  log "健康检查..."
  _check_http "$BACKEND_PORT" "/api/config" && ok "后端 http://localhost:$BACKEND_PORT 响应正常" || warn "后端还在启动中，请稍等..."
  _check_http "$FRONTEND_PORT" "/" && ok "前端 http://localhost:$FRONTEND_PORT 响应正常" || warn "前端还在启动中，请稍等..."
  echo ""
  log "管理面板: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
}

# ─── 停止 ───────────────────────────────────

do_stop() {
  log "停止全部服务..."
  echo ""

  # 先停后端(Dashboard + watchdog)，防止 watchdog 在 presales 被杀后自动重启
  _kill_by_pid backend
  _kill_port "$BACKEND_PORT"
  ok "后端已停止"

  _kill_presales
  ok "Presales daemon 已停止"

  _kill_by_pid frontend
  _kill_port "$FRONTEND_PORT"
  ok "前端已停止"

  pkill -f 'npx vite' 2>/dev/null || true
  pkill -f 'npm exec vite' 2>/dev/null || true

  echo ""
  log "全部服务已停止"
}

# ─── 重启 ───────────────────────────────────

do_restart() {
  do_stop
  sleep 2
  echo ""
  do_start
}

# ─── 状态 ───────────────────────────────────

do_status() {
  log "服务状态"
  echo ""

  local pid status

  # 后端
  pid="$(_read_pid backend)"
  if _is_running "$pid"; then
    if _check_http "$BACKEND_PORT" "/api/config"; then
      ok "后端:     ${GREEN}运行中${NC}  PID=$pid  端口=$BACKEND_PORT  HTTP=OK"
    else
      warn "后端:     ${YELLOW}进程存活但 HTTP 无响应${NC}  PID=$pid"
    fi
  else
    fail "后端:     ${RED}未运行${NC}"
  fi

  # 前端
  pid="$(_read_pid frontend)"
  if _is_running "$pid"; then
    if _check_http "$FRONTEND_PORT" "/"; then
      ok "前端:     ${GREEN}运行中${NC}  PID=$pid  端口=$FRONTEND_PORT  HTTP=OK"
    else
      warn "前端:     ${YELLOW}进程存活但 HTTP 无响应${NC}  PID=$pid"
    fi
  else
    fail "前端:     ${RED}未运行${NC}"
  fi

  # Presales
  pid="$(_read_pid presales)"
  if _is_running "$pid"; then
    ok "Presales: ${GREEN}运行中${NC}  PID=$pid"
  else
    fail "Presales: ${RED}未运行${NC}"
  fi

  # Python 版本
  echo ""
  local py_ver
  py_ver="$("$VENV_PY" --version 2>/dev/null || echo '未知')"
  ok "Python:   $py_ver ($VENV_PY)"
  echo ""
}

# ─── 入口 ───────────────────────────────────

case "${1:-}" in
  start)   do_start   ;;
  stop)    do_stop    ;;
  restart) do_restart ;;
  status)  do_status  ;;
  *)
    echo "闲鱼管家 · 服务管理"
    echo ""
    echo "用法:  bash service.sh <命令>"
    echo ""
    echo "命令:"
    echo "  start     启动全部服务（后端 + 前端 + presales daemon）"
    echo "  stop      停止全部服务"
    echo "  restart   重启全部服务"
    echo "  status    查看服务状态"
    echo ""
    ;;
esac
