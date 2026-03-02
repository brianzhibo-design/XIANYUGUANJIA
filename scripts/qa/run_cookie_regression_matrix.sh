#!/usr/bin/env bash
set -euo pipefail

# Cookie 自动续期回归矩阵（一键）
# 用法:
#   bash scripts/qa/run_cookie_regression_matrix.sh
#   PYTEST_BIN=.venv/bin/pytest bash scripts/qa/run_cookie_regression_matrix.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTEST_BIN="${PYTEST_BIN:-.venv/bin/pytest}"
if [[ ! -x "$PYTEST_BIN" ]]; then
  PYTEST_BIN="pytest"
fi

run_case() {
  local case_id="$1"
  local title="$2"
  local target="$3"
  echo
  echo "================================================================"
  echo "[$case_id] $title"
  echo "CMD: $PYTEST_BIN -q -o addopts='' $target"
  echo "----------------------------------------------------------------"
  "$PYTEST_BIN" -q -o addopts='' "$target"
}

run_case "M1" "正常恢复（cookie更新 -> token重取 -> WS重连）" \
  "tests/test_lite_cookie_renewal_automation.py::test_cookie_renewal_success_flow"

run_case "M2" "风控失败退避（风险码FAIL_SYS_USER_VALIDATE触发退避和预算）" \
  "tests/test_lite_cookie_renewal_automation.py::test_risk_branch_backoff_and_budget_to_waiting_cookie"

run_case "M3" "cookie未更新等待（cookie源为空进入waiting_new_cookie，避免死循环）" \
  "tests/test_lite_cookie_renewal_automation.py::test_empty_cookie_source_enters_waiting_state_not_loop"

run_case "M4" "恢复后WS连接上下文同步（device_id/my_user_id同步后重连）" \
  "tests/test_lite_cookie_renewal.py::test_cookie_renewal_updates_ws_auth_context_for_reconnect"

run_case "M5" "重复恢复抑制（同指纹cookie失败时不重复恢复）" \
  "tests/test_lite_cookie_renewal_automation.py::test_cookie_renewal_duplicate_recovery_waiting_cookie"

echo
cat <<'EOF2'
✅ Cookie 自动续期回归矩阵执行完成。
建议补充执行（可选，验证子集兼容）：
  .venv/bin/pytest -q -o addopts='' tests/test_lite_cookie_renewal.py tests/test_lite_stack.py
EOF2
