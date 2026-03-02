# XY-AUDIT-05 SRE发布与运行稳定性审查报告

- 审查时间：2026-03-02（GMT+8）
- 审查范围：`/Users/brianzhibo/Documents/New project/xianyu-openclaw`
- 审查方式：只读（代码/文档/脚本/运行日志抽样）
- 结论级别：**有条件通过（需补齐可观测与30分钟恢复手册）**

---

## 一、执行摘要

**状态**：核心“检测→恢复”链路已具备雏形（`token_error`、`cookie_update_required`、`risk_control`、`recover`动作均已落地）。  
**影响**：在“Cookie过期/鉴权失败”场景可较快定位并触发恢复；但缺少统一的线上故障30分钟恢复SOP与强制告警闭环，存在 MTTR 漂移风险。  
**动作**：建议以“告警规则 + 可执行手册 + 恢复演练”三件套在本周补齐。  
**预计恢复时间（治理完成）**：3~5个工作日可将高风险项降为中风险。

---

## 二、必须检查项结论

## 1) presales 自动恢复路径在日志中的可诊断性

### 结论：**部分满足（中等可诊断）**

已观察到完整关键事件：
- 失败信号：`Token API failed: ['FAIL_SYS_USER_VALIDATE', 'RGV587...']`
- 风险动作：`Auth/risk failure detected, suspend reconnect until cookie is updated`
- 恢复后信号：`Connected to Goofish WebSocket transport`

证据：
- `data/module_runtime/presales.log`（2026-02-28 21:21:13、2026-03-01 11:38:41、2026-03-01 12:19:02 等）
- `src/dashboard_server.py` 中风险扫描与恢复状态聚合：`_risk_control_status_from_logs`、`_maybe_auto_recover_presales`

不足：
- 日志未统一输出“恢复事务ID/阶段耗时/触发来源（自动或手动）”，跨组件关联排障仍偏人工。
- 目前主要基于 tail 文本模式判断，缺少结构化事件（JSON）与指标化（counter/histogram）。

## 2) token_error / cookie_update_required / risk_control 是否可用于快速定位

### 结论：**基本满足（可快速定位）**

定位能力：
- `token_error` 具备错误分型（`FAIL_SYS_USER_VALIDATE` / `RGV587_SERVER_BUSY` / `TOKEN_API_FAILED` / `WS_HTTP_400`）
- `cookie_update_required` 与 `FAIL_SYS_USER_VALIDATE`关联明确
- `risk_control` 输出 `level/label/score/signals/last_event/last_event_at`

证据：
- `src/dashboard_server.py`：
  - 风险模式词：`_RISK_BLOCK_PATTERNS` / `_RISK_WARN_PATTERNS`
  - 状态聚合输出字段：`token_error`、`cookie_update_required`、`risk_control`、`recovery`

风险点：
- 误报/漏报依赖关键词命中，规则需要版本化与回归测试。
- 未见这些状态与统一告警平台的强绑定（主要停留在页面/日志层）。

## 3) 服务重启/恢复命令路径是否明确且幂等

### 结论：**满足（命令路径清晰，具备幂等特性）**

明确命令路径：
- CLI：`python -m src.cli module --action restart|recover --target presales`
- Unix：`scripts/unix/recover_presales.sh`
- Windows：`scripts/windows/module_recover.bat`

幂等性证据：
- `_start_background_module` 已处理 `already_running`
- `_stop_background_module` 对 `not_running/pid_not_alive` 有显式返回
- `recover` 流程为 stop → 清理运行态（`.json/.pid/.lock`）→ start，并返回 `recovered` 判断

证据：
- `src/cli.py`（`_start_background_module`、`_stop_background_module`、`_clear_module_runtime_state`、`action==recover`）
- `README.md` / `USER_GUIDE.md` / `scripts/*` 含可执行样例

## 4) 线上故障时30分钟内恢复的操作手册是否充分

### 结论：**不满足（关键缺口）**

发现：
- 项目内未见专门的 incident runbook / 30分钟恢复SOP 文档（`docs/` 仅见计划与架构类文档、QA结论）。
- 现有 README/USER_GUIDE 提供命令清单，但缺少“按分钟推进”的应急决策树、升级路径、止血策略与回退条件。

影响：
- 值班人员可“执行命令”，但不一定能在30分钟内稳定完成“诊断-恢复-验证-通报”。

---

## 三、SLO风险评估

| 风险项 | 当前等级 | 影响 | 说明 |
|---|---|---|---|
| 鉴权失败导致售前不可用（Cookie/token） | 高 | 首响SLO、转化率 | 已有检测和恢复动作，但缺少统一告警与SOP闭环 |
| 风控/封控误判或漏判 | 中 | 恢复策略选择错误 | 关键词规则驱动，需规则测试与版本管理 |
| 恢复流程可观测不足（缺事务追踪） | 中 | MTTR拉长 | 无恢复链路ID、分阶段耗时、失败分类聚合 |
| 文档化应急操作不足（30分钟恢复） | 高 | 故障扩散与升级延迟 | 无标准化值班手册、角色分工与升级门槛 |

**综合判断**：当前系统具备恢复能力，但**SRE可运营性未达“30分钟稳定恢复”标准**。建议在上线/扩大流量前完成应急治理最小集。

---

## 四、必须补齐的监控/告警项（P0/P1）

## P0（上线前必须）
1. **Presales 可用性告警**
   - 指标：`presales_process_alive`、`xianyu_connected`
   - 规则：连续 2~3 分钟不可用即告警（电话/IM）。
2. **鉴权失败告警**
   - 指标：`token_error{type}`（至少含 `FAIL_SYS_USER_VALIDATE`）
   - 规则：5分钟窗口出现>=1次关键错误触发告警。
3. **Cookie更新需求告警**
   - 指标：`cookie_update_required == true`
   - 规则：持续 > 3 分钟未恢复升级到人工处理。
4. **自动恢复失败告警**
   - 指标：`recovery.auto_recover_triggered` + `last_auto_recover_result.error`
   - 规则：自动恢复失败立即告警并附一键手动恢复指令。
5. **恢复超时告警（MTTR守护）**
   - 指标：从首次故障到`Connected`恢复耗时
   - 规则：> 10 分钟黄色，> 20 分钟红色（30分钟SLO前置拦截）。

## P1（两周内）
6. **风险控制等级趋势告警**
   - 指标：`risk_control.level/score` 连续上升趋势。
7. **WebSocket异常密度告警**
   - 指标：`WS_HTTP_400`、重连次数/分钟。
8. **恢复动作审计告警**
   - 指标：`recover/restart/stop/start` 操作人、来源、结果。
9. **业务结果告警（SLO直连）**
   - 指标：首响P95、报价成功率、回退率、每小时回复量异常下跌。

---

## 五、应急建议（面向30分钟恢复）

1. 新增 `docs/runbooks/incident-presales-30min.md`（按时间片：0-5/5-10/10-20/20-30分钟）。
2. 固化“先恢复后定位”流程：
   - 检查状态 → 判断是否 `cookie_update_required` → 执行 `module recover` → 验证 `Connected` 与核心SLO回升。
3. 给恢复链路增加结构化日志字段：`incident_id`、`recover_stage`、`elapsed_ms`、`error_type`、`trigger_source`。
4. 每周一次故障演练（至少覆盖：Cookie过期、WS 400风控、进程假活）。
5. 建立升级机制：10分钟未恢复自动升级L2，20分钟升级负责人，30分钟触发业务降级策略。

---

## 六、审查结论

**结论：有条件通过。**  
- 工程侧恢复能力与命令幂等性已具备。  
- 但“告警闭环 + 30分钟恢复手册 + 结构化可观测”尚未达标。  

建议将本审查列为发布前阻断项：**补齐P0后再宣告达到SRE稳定性基线**。
