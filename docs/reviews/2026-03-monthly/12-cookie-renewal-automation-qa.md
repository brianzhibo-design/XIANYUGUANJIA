# Cookie续期自动化专项QA报告

- 任务ID：XY-LITE-20260302-B（优先级切换后：Cookie续期自动化专项）
- 执行时间：2026-03-02 14:02 ~ 14:04 (Asia/Shanghai)
- 执行人：暖羊羊（QA）
- 环境：`/Users/brianzhibo/Documents/New project/xianyu-openclaw`

## 1. 测试目标
验证以下链路在“Cookie失效”场景下的自动化行为：
1) 自动检测（识别 `FAIL_SYS_USER_VALIDATE`）
2) 自动恢复（触发 presales recover）
3) WS重连（恢复后连接恢复）
4) 重复恢复抑制（同一Cookie不重复触发recover）

## 2. 测试步骤（可复现）

### Step A：基线确认
- `GET /api/status`
- 期望：系统 running，`token_error=null`，`cookie_update_required=false`
- 结果：满足

### Step B：构造Cookie失效场景
- 向 `data/module_runtime/presales.log` 注入：
  - `token api failed: FAIL_SYS_USER_VALIDATE | qa-injected`
- 再次 `GET /api/status`
- 期望：系统识别 token 错误并提示需更新Cookie
- 结果：
  - `token_error=FAIL_SYS_USER_VALIDATE`
  - `cookie_update_required=true`
  - `recovery.reason=waiting_cookie_update`

### Step C：触发自动恢复
- `POST /api/update-cookie`（使用当前cookie+附加字段改变指纹：`qa_renewal_probe=1`）
- 期望：自动触发 presales recover
- 结果：
  - 返回 `message=Cookie updated and presales recovery triggered`
  - `auto_recover.triggered=true`
  - `auto_recover.message=recover_ok`
  - recover结果显示：`stopped pid=94761`，`started pid=29137`

### Step D：验证重复恢复抑制
- 再注入一次 `FAIL_SYS_USER_VALIDATE`（`qa-injected-2`）
- 连续两次 `GET /api/status`（不更新cookie）
- 期望：不重复触发recover
- 结果：
  - 两次均为 `recovery.reason=same_cookie_already_recovered`
  - `recovery.stage=waiting_reconnect`
  - 未出现新一轮recover触发信号（符合抑制预期）

### Step E：验证WS重连
- 检查 `data/module_runtime/presales.log`（recover后窗口）
- 观察：
  - 有重启启动日志：`[2026-03-02 14:02:51] start target=presales ...`
  - 但后续出现：`Auth/risk failure detected, suspend reconnect until cookie is updated`
  - 未出现新的 `Connected to Goofish WebSocket transport`

## 3. 观测指标与结果

| 指标 | 结果 | 判定 |
|---|---|---|
| 自动检测 | 成功识别 `FAIL_SYS_USER_VALIDATE`，状态降级并要求更新Cookie | PASS |
| 自动恢复触发 | `update-cookie` 后 recover 成功触发并重启 presales | PASS |
| 重复恢复抑制 | 同Cookie下重复失败信号不再重复recover | PASS |
| WS重连 | recover后未恢复到 connected，仍被鉴权/风控阻断 | FAIL |

## 4. 发现问题

### P1：自动恢复后未完成WS可用性恢复
- 现象：recover能执行，但链路仍停留在 `waiting_reconnect`，日志显示鉴权仍失败并暂停重连。
- 影响：Cookie续期自动化闭环不完整（恢复动作成功 ≠ 业务链路恢复成功）。
- 证据：
  - `data/module_runtime/presales.log` 中 14:02:51 启动后紧接鉴权失败告警
  - 状态持续 `token_error=FAIL_SYS_USER_VALIDATE`

## 5. QA结论

**结论：FAIL**

原因：虽然自动检测、自动恢复触发、重复恢复抑制均通过，但**WS重连未恢复成功**，Cookie续期自动化链路未形成可用闭环，不满足“自动恢复后可继续稳定服务”的质量门槛。

## 6. 建议动作

1. 在 recover 后增加“连接成功确认”二次门禁：若 N 秒内未出现 `Connected to Goofish WebSocket transport`，自动标记 recover failed 并告警。  
2. 对 `FAIL_SYS_USER_VALIDATE` 增加 Cookie质量校验前置（关键字段/新鲜度/来源合法性），避免无效cookie触发“假恢复”。  
3. 增加恢复状态机：`recover_triggered -> reconnecting -> connected/failed`，避免 `waiting_reconnect` 长时间悬挂。  
4. Dashboard显示 recover结果时区分：`进程重启成功` 与 `链路恢复成功`（两层状态）。

## 7. 证据文件

- 原始证据：`tmp/qa/cookie_renewal_evidence.json`
- 关键日志：`data/module_runtime/presales.log`
