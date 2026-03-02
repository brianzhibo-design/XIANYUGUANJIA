#!/usr/bin/env bash
set -euo pipefail

# Cookie 续期日志过滤模板
# 用法:
#   bash scripts/qa/filter_cookie_recovery_logs.sh
#   LOG_FILE=data/module_runtime/presales.log WINDOW_MIN=30 bash scripts/qa/filter_cookie_recovery_logs.sh

LOG_FILE="${LOG_FILE:-data/module_runtime/presales.log}"
WINDOW_MIN="${WINDOW_MIN:-20}"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "[ERR] log file not found: $LOG_FILE" >&2
  exit 1
fi

echo "# source=$LOG_FILE"
echo "# window(last minutes)=$WINDOW_MIN"

# 最近窗口截取（按行近似，避免全文件扫描成本过高）
TAIL_LINES="${TAIL_LINES:-5000}"
TMP="$(mktemp)"
tail -n "$TAIL_LINES" "$LOG_FILE" > "$TMP"

echo
printf '=== A. 核心恢复信号（成功/失败/抑制） ===\n'
grep -E "FAIL_SYS_USER_VALIDATE|Token API failed|Connected to Goofish WebSocket transport|Auth/risk failure detected|same_cookie_already_recovered|waiting_new_cookie|renew_(failed|succeeded|waiting_cookie|suppressed)" "$TMP" || true

echo
printf '=== B. 进程恢复动作 ===\n'
grep -E "start target=presales|stopped pid=|started pid=|recover" "$TMP" || true

echo
printf '=== C. 最近状态快照（若日志有状态行） ===\n'
grep -E "lite_cookie_renewal_status=|recovery\.stage|cookie_update_required|token_error" "$TMP" || true

rm -f "$TMP"
