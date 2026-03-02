# 23-cookie-regression-matrix

- 任务ID：XY-COOKIE-20260302-O
- 目标：并行准备“自动续期”回归测试矩阵，支持主修后一键/半自动复测
- 工作目录：`/Users/brianzhibo/Documents/New project/xianyu-openclaw`
- 产出时间：2026-03-02

---

## 1) 回归矩阵（5大场景）

| Matrix ID | 场景 | 覆盖用例/动作 | 关键通过标准（Gate） |
|---|---|---|---|
| M1 | 正常恢复 | `test_cookie_renewal_success_flow` | `renew()==True`；`recover_count+1`；`last_cookie_refresh/last_token_refresh` 非空；`ws.force_reconnect` 被调用 |
| M2 | 风控失败退避 | `test_risk_branch_backoff_and_budget_to_waiting_cookie` | 捕获 `FAIL_SYS_USER_VALIDATE`；发生 backoff；达到预算后进入 `waiting_new_cookie` |
| M3 | cookie未更新等待 | `test_empty_cookie_source_enters_waiting_state_not_loop` | cookie源为空时进入 `waiting_new_cookie`；设置 `next_retry_at`；无重连风暴 |
| M4 | 恢复后WS连接成功（上下文一致性） | `test_cookie_renewal_updates_ws_auth_context_for_reconnect` | 续期后 WS `cookie/device_id/my_user_id` 与 API 侧同步；触发 `force_reconnect` |
| M5 | 重复恢复抑制 | `test_cookie_renewal_duplicate_recovery_waiting_cookie` | 同指纹 cookie 连续失败时不重复恢复；审计日志出现 `renew_waiting_cookie` / `same_cookie_fingerprint` |

> 说明：M4 当前以“WS鉴权上下文一致 + 可重连调用”作为自动化门禁；生产/联调阶段仍需配合日志确认出现 `Connected to Goofish WebSocket transport`。

---

## 2) 一键回归脚本（主入口）

已新增脚本：`scripts/qa/run_cookie_regression_matrix.sh`

执行：

```bash
bash scripts/qa/run_cookie_regression_matrix.sh
```

或指定 pytest：

```bash
PYTEST_BIN=.venv/bin/pytest bash scripts/qa/run_cookie_regression_matrix.sh
```

该脚本串行执行 M1~M5 五个 case，适合主修完成后的快速“烟囱回归”。

---

## 3) 半自动联调命令清单（接口+日志）

> 适用于“代码通过单测后，验证运行态恢复链路”。

### 3.1 基线状态

```bash
curl -s http://127.0.0.1:18080/api/status | python -m json.tool
```

关注字段：
- `token_error`
- `cookie_update_required`
- `recovery.stage`
- `recovery.reason`

### 3.2 注入风控失败信号（模拟）

```bash
echo "$(date '+%F %T') | ERROR | token api failed: FAIL_SYS_USER_VALIDATE | qa-regression" >> data/module_runtime/presales.log
```

### 3.3 更新 cookie 触发自动恢复

```bash
COOKIE_VAL="$(grep -E '^XIANYU_COOKIE_1=' .env | sed 's/^XIANYU_COOKIE_1=//')"
COOKIE_VAL="${COOKIE_VAL};qa_regression_probe=1"

curl -s -X POST http://127.0.0.1:18080/api/update-cookie \
  -H 'Content-Type: application/json' \
  -d "{\"cookie\": \"${COOKIE_VAL}\"}" | python -m json.tool
```

### 3.4 再次注入并验证重复恢复抑制

```bash
echo "$(date '+%F %T') | ERROR | token api failed: FAIL_SYS_USER_VALIDATE | qa-regression-2" >> data/module_runtime/presales.log
curl -s http://127.0.0.1:18080/api/status | python -m json.tool
sleep 2
curl -s http://127.0.0.1:18080/api/status | python -m json.tool
```

预期：`recovery.reason` 出现 `same_cookie_already_recovered`，且不重复触发 recover。

---

## 4) 日志过滤模板

已新增模板脚本：`scripts/qa/filter_cookie_recovery_logs.sh`

执行：

```bash
bash scripts/qa/filter_cookie_recovery_logs.sh
```

可指定日志文件：

```bash
LOG_FILE=data/module_runtime/presales.log WINDOW_MIN=30 bash scripts/qa/filter_cookie_recovery_logs.sh
```

模板会聚焦以下关键线索：
- 风控/鉴权失败：`FAIL_SYS_USER_VALIDATE` / `Token API failed`
- 恢复成功信号：`Connected to Goofish WebSocket transport`
- 恢复受阻信号：`Auth/risk failure detected`
- 重复恢复抑制：`same_cookie_already_recovered` / `renew_waiting_cookie`
- 进程动作：`start target=presales` / `stopped pid=` / `started pid=`

---

## 5) 复测建议节奏（压缩二次验收）

1. **主修提交后立即执行一键脚本（M1~M5）**：5个关键面先做 gate。  
2. **若M4/M5通过，再做半自动联调**：补 runtime 证据（status + presales.log）。  
3. **结果归档**：把本次命令输出与过滤日志落到 `tmp/qa/`，供双审直接复核。

---

## 6) 本次新增文件

- `scripts/qa/run_cookie_regression_matrix.sh`
- `scripts/qa/filter_cookie_recovery_logs.sh`
- `docs/reviews/2026-03-monthly/23-cookie-regression-matrix.md`

