# 21-cookie-dual-review-checklist（自动续期策略审计 + 双审预检）

- 任务ID：XY-COOKIE-20260302-M
- 复审负责人：慢羊羊（subagent）
- 结论定位：**当前不满足双审放行条件（需先做最小修复）**

---

## A. 已审阅证据范围（含代码）

### 文档证据
- `docs/reviews/2026-03-monthly/11-cookie-renewal-automation-impl.md`
- `docs/reviews/2026-03-monthly/15-cookie-ws-reconnect-fix.md`
- `docs/reviews/2026-03-monthly/16-cookie-ws-reconnect-qa2.md`
- `tmp/qa/cookie_renewal_evidence.json`
- `tmp/qa/cookie_ws_reconnect_qa2_evidence.json`

### 代码证据
- `src/lite/cookie_renewal.py`
- `src/lite/ws_client.py`
- `src/lite/__main__.py`
- `src/dashboard_server.py:2406-2448`（恢复状态机）
- `src/modules/messages/ws_live.py:794-816`（鉴权失败后重连/挂起逻辑）

### 证据完整性备注
- 本目录缺少“17号文档”；当前按 11/15/16 + 运行证据完成审计。

---

## B. 审计结论（聚焦“WS恢复通过”的最小修复面）

### 关键发现 1（主因）
`15` 的修复主要落在 **Lite链路**（`src/lite/*`），而 QA 失败证据来自 **presales 主链路**（`dashboard_server + ws_live`）。

- Lite 侧修了 auth context 同步（`update_auth_context`），但主链路判定/恢复逻辑在：
  - `src/dashboard_server.py:2415-2431`（recover 触发与 same-cookie 抑制）
  - `src/modules/messages/ws_live.py:805`（鉴权失败后挂起等待 cookie 更新）
- 因此出现“恢复动作触发了，但 WS 仍未确认恢复”的现象。

### 关键发现 2（状态机门禁不足）
`dashboard_server._maybe_auto_recover_presales()` 把“触发 recover”与“链路已恢复”解耦，缺少连接成功门禁。

- 现状：同 cookie 会进入 `waiting_reconnect`（`2415-2417`），但没有强校验“recover后 N 秒内必须出现 Connected”。
- 结果：可能长期停留等待态，且对外看起来像“触发成功但不可用”。

### 关键发现 3（抑制策略可能过硬）
`same_cookie_already_recovered` 抑制策略可防风暴，但在“recover后仍失败”场景下，可能阻断必要重试/失败升级。

---

## C. 必须改（Must Fix）

> 目标：以最小改动让“WS恢复通过”可判定、可回归、可双审。

1. **补“连接成功门禁”到恢复状态机（必须）**
   - 位置：`src/dashboard_server.py` 恢复聚合逻辑。
   - 要求：`recover_triggered` 后进入明确窗口（如 30~90s）校验：
     - 出现 `Connected to Goofish WebSocket transport` 且时间晚于 `last_auto_recover_at`；
     - 且窗口内无新的 `FAIL_SYS_USER_VALIDATE` 终态。
   - 未满足则转 `recover_failed`（不要长期挂 `waiting_reconnect`）。

2. **把“恢复成功判定”从“触发成功”升级为“链路成功”（必须）**
   - 当前 `auto_recover_triggered=true` 仅表示触发了 `module_console.control(recover)`。
   - 必须新增字段（或等价逻辑）区分：`recover_triggered` vs `recover_confirmed`。

3. **补对应回归测试（必须）**
   - 至少覆盖：
     - recover触发但未连接成功 => FAIL（`recover_failed`）；
     - recover后出现Connected => PASS（`healthy`或`connected`）；
     - same-cookie 抑制仍保留但不掩盖失败终态。

---

## D. 可后置（Should Later）

1. **Lite 与主链路恢复策略统一化**
   - 把 Lite 的闭环可观测字段（`last_cookie_refresh/last_token_refresh/recover_count`）向主链路对齐。

2. **cookie质量前置校验增强**
   - 在 recover 前增加 cookie freshness/关键字段一致性检查，降低“无效cookie触发假恢复”。

3. **恢复指标化**
   - 增加 `recovery_latency_seconds`、`recover_failed_total`、`waiting_reconnect_duration` 指标，便于 SRE 门禁。

---

## E. 双审预检清单模板（主审/复审可直接打勾）

> 用法：主审先勾“主审”，复审独立复勾“复审”，任一项不通过即打回。

| 检查项 | 主审 | 复审 | 证据/备注 |
|---|---|---|---|
| 1. 失败证据复现：`FAIL_SYS_USER_VALIDATE` 可稳定触发 | [ ] | [ ] | 日志 + 状态截图 |
| 2. 更新cookie后自动恢复会触发（仅触发层） | [ ] | [ ] | `auto_recover.triggered=true` |
| 3. 已实现“连接成功门禁”（非仅触发） | [ ] | [ ] | 代码路径 + 测试名 |
| 4. recover窗口内出现 `Connected to Goofish WebSocket transport` | [ ] | [ ] | 时间戳需晚于 `last_auto_recover_at` |
| 5. 若窗口内未连接成功，状态进入 `recover_failed`（非无限 waiting） | [ ] | [ ] | 状态机输出 |
| 6. same-cookie 抑制有效且不掩盖失败终态 | [ ] | [ ] | 连续两次 status 证据 |
| 7. 对应回归测试已新增并通过 | [ ] | [ ] | pytest 输出 |
| 8. 文档11/15/16与当前实现一致，无“文档已修代码未修”偏差 | [ ] | [ ] | diff + 文档引用 |
| 9. 本轮结论：可进入双审放行 | [ ] | [ ] | 仅全部通过时勾选 |

---

## F. 放行门槛（本轮建议）

- **当前建议：不放行**
- **放行前最低条件**：C节 3 个 Must Fix 全部完成，并附一轮 QA 复测证据（可复现 + 可回归）。
