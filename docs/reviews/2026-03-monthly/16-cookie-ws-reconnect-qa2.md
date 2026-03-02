# WS重连鉴权失败修复 - QA预验收复测报告（第二轮）

- 任务ID：XY-COOKIE-20260302-H
- 执行时间：2026-03-02 14:23 ~ 14:24 (Asia/Shanghai)
- 执行人：暖羊羊（QA）
- 工作目录：`/Users/brianzhibo/Documents/New project/xianyu-openclaw`

## 1) 复测目标与输入
基于既有失败证据 `tmp/qa/cookie_renewal_evidence.json` 复用同类注入标记（`qa-injected` / `qa-injected-2`）构造回归场景，验证以下4项：
1. 自动检测
2. 自动恢复触发
3. WS重连成功
4. 重复恢复抑制

本轮新增证据文件：`tmp/qa/cookie_ws_reconnect_qa2_evidence.json`

---

## 2) 可复现步骤（本轮实际执行）

### Step A：读取基线状态
- `GET /api/status`
- 观察：基线已处于 `token_error=FAIL_SYS_USER_VALIDATE`、`recovery.stage=waiting_reconnect`（系统在故障态）

### Step B：复用历史失败标记构造场景
- 向 `data/module_runtime/presales.log` 追加：
  - `2026-03-02 14:02:47 | ERROR | token api failed: FAIL_SYS_USER_VALIDATE | qa-injected`
- 再次 `GET /api/status`
- 观察：保持 `FAIL_SYS_USER_VALIDATE`，自动检测通路仍有效（仍判定鉴权失败）

### Step C：触发自动恢复
- `POST /api/update-cookie`（使用 `.env` 的 `XIANYU_COOKIE_1` + `qa2_probe=1` 改变指纹）
- 返回：`Cookie updated and presales recovery triggered`
- 关键字段：`auto_recover.triggered=true`

### Step D：重复恢复抑制验证
- 再注入：`qa-injected-2`
- 连续两次 `GET /api/status`
- 两次均为：`recovery.reason=same_cookie_already_recovered`，未看到重复触发恢复

### Step E：WS重连验证
- 观察恢复后窗口日志（14:23:47~14:23:48）：
  - 有重启：`start target=presales`
  - 但紧接：`Goofish WebSocket disconnected ... FAIL_SYS_USER_VALIDATE`
  - 且：`Auth/risk failure detected, suspend reconnect until cookie is updated`
- 观察窗口内未出现新的 `Connected to Goofish WebSocket transport`

---

## 3) 四项验收结果

| 验证项 | 结果 | 判定 |
|---|---|---|
| 自动检测 | 状态持续识别 `FAIL_SYS_USER_VALIDATE`，进入/维持恢复态 | PASS |
| 自动恢复触发 | `update-cookie` 返回已触发恢复（`auto_recover.triggered=true`） | PASS |
| WS重连成功 | 恢复后仍鉴权失败并暂停重连，未恢复 connected | **FAIL** |
| 重复恢复抑制 | 二次失败后仍为 `same_cookie_already_recovered`，无重复恢复风暴 | PASS |

---

## 4) 最终结论

**结论：FAIL（不建议进入双审）**

失败阶段定位：
- 失败发生在 **阶段3：WS重连成功验证**。
- 现象为“恢复动作已触发，但链路仍停留在鉴权失败/等待重连态”，未形成可用闭环。

---

## 5) 关键证据路径

1. 本轮结构化证据：
- `tmp/qa/cookie_ws_reconnect_qa2_evidence.json`

2. 复用历史证据（场景来源）：
- `tmp/qa/cookie_renewal_evidence.json`

3. 关键运行日志：
- `data/module_runtime/presales.log`
  - `14:23:47`：`start target=presales`
  - `14:23:48`：`Token API failed: ['FAIL_SYS_USER_VALIDATE', ...]`
  - `14:23:48`：`Auth/risk failure detected, suspend reconnect until cookie is updated`

---

## 6) 残余风险（当前版本）

- 风险1：恢复动作与链路可用性解耦，可能出现“重启成功但业务不可用”的假阳性。
- 风险2：长期停留 `waiting_reconnect` 可能导致服务窗口不可用延长。
- 风险3：若外部cookie质量/风控状态不稳定，当前机制对“恢复成功”判定不够严格。

建议：在恢复流程加入“连接成功门禁”（例如 N 秒内必须出现 `Connected to Goofish WebSocket transport`，否则恢复判定失败并显式告警）。
