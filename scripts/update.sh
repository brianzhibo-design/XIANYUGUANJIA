#!/usr/bin/env bash
# 闲鱼管家 - 在线更新脚本
#
# 用法:
#   bash scripts/update.sh <update-package.tar.gz> [project-root]
#
# 由后端 POST /api/update/apply 自动调用，也可手动执行。
# 流程：备份 → 停服务 → 解压覆盖 → pip install → 重启
set -uo pipefail

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[1;34m'; N='\033[0m'
ok()   { printf "${G}[OK]${N} %s\n" "$1"; }
warn() { printf "${Y}[!!]${N} %s\n" "$1"; }
fail() { printf "${R}[ERR]${N} %s\n" "$1"; }
info() { printf "${B}[>>]${N} %s\n" "$1"; }

PACKAGE_PATH="${1:-}"
PROJECT_ROOT="${2:-$(cd "$(dirname "$0")/.." && pwd)}"
STATUS_FILE="$PROJECT_ROOT/data/update-status.json"

write_status() {
  local status="$1"
  shift
  local extra=""
  if [ $# -gt 0 ]; then
    extra=", $*"
  fi
  mkdir -p "$(dirname "$STATUS_FILE")"
  cat > "$STATUS_FILE" <<EOJSON
{"status": "$status", "timestamp": "$(date '+%Y-%m-%dT%H:%M:%S')"$extra}
EOJSON
}

cleanup_on_error() {
  local backup_tar="$1"
  fail "更新失败，正在回滚..."
  write_status "rolling_back"
  if [ -f "$backup_tar" ]; then
    (cd "$PROJECT_ROOT" && tar xzf "$backup_tar" 2>/dev/null)
    ok "已从备份恢复"
  fi
  write_status "error" "\"message\": \"更新失败已回滚\""
  info "正在重新启动服务..."
  cd "$PROJECT_ROOT"
  if [ -f "start.sh" ]; then
    nohup bash start.sh > logs/start.log 2>&1 &
  fi
  exit 1
}

if [ -z "$PACKAGE_PATH" ]; then
  fail "用法: bash scripts/update.sh <update-package.tar.gz> [project-root]"
  exit 1
fi

if [ ! -f "$PACKAGE_PATH" ]; then
  fail "更新包不存在: $PACKAGE_PATH"
  write_status "error" "\"message\": \"更新包不存在\""
  exit 1
fi

cd "$PROJECT_ROOT"
mkdir -p logs data/backups

info "========================================="
info "闲鱼管家 · 在线更新"
info "========================================="
info "更新包: $PACKAGE_PATH"
info "项目目录: $PROJECT_ROOT"
echo ""

# ═══════════════ 1. 备份 ═══════════════
info "[1/5] 创建备份..."
write_status "backing_up"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_TAR="$PROJECT_ROOT/data/backups/pre-update-${TIMESTAMP}.tar.gz"

BACKUP_ITEMS=""
for item in src scripts client/dist client/src requirements.txt start.sh start.bat quick-start.sh quick-start.bat; do
  if [ -e "$item" ]; then
    BACKUP_ITEMS="$BACKUP_ITEMS $item"
  fi
done

if [ -n "$BACKUP_ITEMS" ]; then
  tar czf "$BACKUP_TAR" $BACKUP_ITEMS 2>/dev/null
  BACKUP_SIZE=$(du -sh "$BACKUP_TAR" | cut -f1)
  ok "备份完成: $BACKUP_SIZE -> data/backups/pre-update-${TIMESTAMP}.tar.gz"
  # Keep only the 3 most recent backups
  ls -t "$PROJECT_ROOT/data/backups/pre-update-"*.tar.gz 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
else
  warn "没有找到需要备份的文件"
  BACKUP_TAR=""
fi

# ═══════════════ 2. 停止服务 ═══════════════
info "[2/5] 停止运行中的服务..."
write_status "stopping"

for port in 8091 5173; do
  PIDS=$(lsof -ti :"$port" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
    ok "已向端口 $port 发送 SIGTERM"
  fi
done
sleep 3
for port in 8091 5173; do
  PIDS=$(lsof -ti :"$port" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    warn "端口 $port 强制终止 (SIGKILL)"
  fi
done
sleep 1

# ═══════════════ 3. 解压覆盖 ═══════════════
info "[3/5] 解压并覆盖源码..."
write_status "extracting"

TEMP_DIR=$(mktemp -d)
tar xzf "$PACKAGE_PATH" -C "$TEMP_DIR" 2>/dev/null
if [ $? -ne 0 ]; then
  fail "解压更新包失败"
  cleanup_on_error "${BACKUP_TAR:-/dev/null}"
fi

EXTRACTED_DIR=$(find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -1)
if [ -z "$EXTRACTED_DIR" ]; then
  EXTRACTED_DIR="$TEMP_DIR"
fi

PRESERVE_LIST="data .env config/config.yaml logs .venv node_modules vendor"

for item in src scripts client requirements.txt start.sh start.bat quick-start.sh quick-start.bat; do
  SRC_ITEM="$EXTRACTED_DIR/$item"
  DST_ITEM="$PROJECT_ROOT/$item"

  if [ ! -e "$SRC_ITEM" ]; then
    continue
  fi

  skip=false
  for preserve in $PRESERVE_LIST; do
    if [ "$item" = "$preserve" ]; then
      skip=true
      break
    fi
  done
  if [ "$skip" = true ]; then
    continue
  fi

  if [ -d "$SRC_ITEM" ]; then
    rm -rf "$DST_ITEM"
    cp -a "$SRC_ITEM" "$DST_ITEM"
  else
    cp -a "$SRC_ITEM" "$DST_ITEM"
  fi
done

ok "源码覆盖完成"
rm -rf "$TEMP_DIR"

# ═══════════════ 4. 更新依赖 ═══════════════
info "[4/5] 检查依赖更新..."
write_status "installing_deps"

VENV_PIP=""
if [ -f "$PROJECT_ROOT/.venv/bin/pip" ]; then
  VENV_PIP="$PROJECT_ROOT/.venv/bin/pip"
elif [ -f "$PROJECT_ROOT/.venv/Scripts/pip.exe" ]; then
  VENV_PIP="$PROJECT_ROOT/.venv/Scripts/pip.exe"
fi

if [ -n "$VENV_PIP" ] && [ -f "$PROJECT_ROOT/requirements.txt" ]; then
  if [ -f "$BACKUP_TAR" ]; then
    OLD_REQ_HASH=$(tar xzf "$BACKUP_TAR" -O requirements.txt 2>/dev/null | shasum -a 256 | cut -d' ' -f1)
    NEW_REQ_HASH=$(shasum -a 256 "$PROJECT_ROOT/requirements.txt" | cut -d' ' -f1)
    if [ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]; then
      info "requirements.txt 已变化，正在安装新依赖..."
      $VENV_PIP install -r "$PROJECT_ROOT/requirements.txt" -q 2>&1 | tail -3
      ok "依赖安装完成"
    else
      ok "requirements.txt 未变化，跳过"
    fi
  else
    info "无备份可比较，执行依赖安装..."
    $VENV_PIP install -r "$PROJECT_ROOT/requirements.txt" -q 2>&1 | tail -3
    ok "依赖安装完成"
  fi
else
  warn "未找到 venv pip 或 requirements.txt，跳过依赖安装"
fi

# ═══════════════ 4.5 配置迁移 ═══════════════
CONFIG_YAML="$PROJECT_ROOT/config/config.yaml"
if [ -f "$CONFIG_YAML" ] && grep -q 'safety_margin: 0\.03' "$CONFIG_YAML" 2>/dev/null; then
  sed -i.migbak 's/safety_margin: 0\.03/safety_margin: 0.0/' "$CONFIG_YAML"
  rm -f "${CONFIG_YAML}.migbak" 2>/dev/null
  ok "已自动将 safety_margin 从 0.03 修正为 0.0"
fi

# ═══════════════ 5. 重启服务 ═══════════════
info "[5/5] 重新启动服务..."
write_status "restarting"

NEW_VERSION="unknown"
if [ -f "$PROJECT_ROOT/src/__init__.py" ]; then
  NEW_VERSION=$(sed -n 's/.*__version__[[:space:]]*=[[:space:]]*["\x27]\([^"\x27]*\).*/\1/p' \
    "$PROJECT_ROOT/src/__init__.py" 2>/dev/null)
  [ -z "$NEW_VERSION" ] && NEW_VERSION="unknown"
fi

cd "$PROJECT_ROOT"
if [ -f "start.sh" ]; then
  nohup bash start.sh > logs/start.log 2>&1 &
  ok "服务启动中..."
else
  warn "未找到 start.sh，请手动启动服务"
  write_status "done" "\"version\": \"$NEW_VERSION\", \"message\": \"更新完成（需手动启动）\""
  rm -f "$PACKAGE_PATH" 2>/dev/null || true
  exit 0
fi

# ═══════════════ 5.1 健康检查 ═══════════════
info "等待健康检查..."
HEALTH_OK=false
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8091/api/health >/dev/null 2>&1; then
    HEALTH_OK=true
    break
  fi
  sleep 1
done

if [ "$HEALTH_OK" = true ]; then
  write_status "done" "\"version\": \"$NEW_VERSION\", \"message\": \"更新完成\""
  rm -f "$PACKAGE_PATH" 2>/dev/null || true
  echo ""
  info "========================================="
  ok "更新完成! 新版本: v${NEW_VERSION}"
  info "========================================="
else
  fail "服务未通过健康检查 (30s 超时)，触发回滚"
  cleanup_on_error "${BACKUP_TAR:-/dev/null}"
fi
